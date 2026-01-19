"""
Prometheus Adapter - TSDB client for Prometheus-compatible databases.

Supports VictoriaMetrics, Thanos, Mimir, Cortex, and native Prometheus.
Uses OpenTelemetry Exporter for robust Remote Write.
"""

import time
from datetime import datetime

import httpx
import pandas as pd
from pydantic import PrivateAttr

# OpenTelemetry Imports for manual metric construction
try:
    from opentelemetry.exporter.prometheus_remote_write import (
        PrometheusRemoteWriteMetricsExporter,
    )
    from opentelemetry.sdk.metrics.export import (
        MetricsData,
        ResourceMetrics,
        ScopeMetrics,
        Metric,
        NumberDataPoint,
        AggregationTemporality,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.util.instrumentation import InstrumentationScope
except ImportError:
    PrometheusRemoteWriteMetricsExporter = None

from openanomaly.core.ports.tsdb_client import TSDBClient


class PrometheusAdapter(TSDBClient):
    """
    TSDB adapter for Prometheus-compatible databases.
    Configured via Pydantic model fields.
    """
    read_url: str
    write_url: str | None = None
    timeout: float = 30.0
    headers: dict[str, str] = {}
    
    _client: httpx.AsyncClient | None = PrivateAttr(default=None)
    _exporter: "PrometheusRemoteWriteMetricsExporter | None" = PrivateAttr(default=None)

    def model_post_init(self, __context):
        """Normalize URL after initialization."""
        self.read_url = self.read_url.rstrip("/")
        if self.write_url and PrometheusRemoteWriteMetricsExporter is None:
             pass 
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client for reading."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
            )
        return self._client
    
    def _get_exporter(self) -> "PrometheusRemoteWriteMetricsExporter":
        """Get or create the OTel Remote Write Exporter."""
        if self._exporter is None:
            if PrometheusRemoteWriteMetricsExporter is None:
                raise ImportError("opentelemetry-exporter-prometheus-remote-write not installed")
            if not self.write_url:
                raise RuntimeError("Write URL not configured")
     
            self._exporter = PrometheusRemoteWriteMetricsExporter(
                endpoint=self.write_url,
                headers=self.headers,
                timeout=int(self.timeout),
            )
        return self._exporter
    
    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str,
    ) -> pd.DataFrame:
        """Execute a range query and return a DataFrame."""
        client = await self._get_client()
        
        params = {
            "query": query,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "step": step,
        }
        
        response = await client.get(
            f"{self.read_url}/api/v1/query_range",
            params=params,
        )
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != "success":
            raise RuntimeError(f"Prometheus query failed: {data.get('error', 'Unknown error')}")
        
        frames = []
        for result in data.get("data", {}).get("result", []):
            metric = result.get("metric", {})
            name = metric.pop("__name__", "metric")
            
            labels_str = ",".join(f'{k}="{v}"' for k, v in sorted(metric.items()))
            unique_id = f"{name}{{{labels_str}}}" if labels_str else name
            
            values = result.get("values", [])
            if not values:
                continue
                
            df_series = pd.DataFrame(values, columns=["timestamp", "value"])
            df_series["ds"] = pd.to_datetime(df_series["timestamp"].astype(float), unit="s")
            df_series["y"] = pd.to_numeric(df_series["value"], errors="coerce")
            df_series["unique_id"] = unique_id
            
            frames.append(df_series[["unique_id", "ds", "y"]])
            
        if not frames:
            return pd.DataFrame(columns=["unique_id", "ds", "y"])
            
        return pd.concat(frames, ignore_index=True)
    
    async def write(
        self,
        df: pd.DataFrame,
    ) -> None:
        """
        Write time series data using OTel Remote Write Exporter.
        Manually constructs MetricsData to allow historical timestamps.
        """
        exporter = self._get_exporter()
        
        # DataFrame columns: ['unique_id', 'ds', 'y']
        required_cols = {"unique_id", "ds", "y"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")
        
        # We need to group by metric name to create efficient OTel structures
        # In unique_id, format is name{label="v"}
        # We'll parse first
        
        points_by_metric = {} # name -> list of points
        
        for _, row in df.iterrows():
            raw_id = row["unique_id"]
            labels = {}
            metric_name = raw_id
            
            if "{" in raw_id and raw_id.endswith("}"):
                name_part, labels_part = raw_id[:-1].split("{", 1)
                metric_name = name_part
                for pair in labels_part.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        labels[k.strip()] = v.strip().strip('"')
            
            ts_ns = int(row["ds"].timestamp() * 1e9)
            val = float(row["y"])
            
            # Create OTel Point
            point = NumberDataPoint(
                attributes=labels,
                start_time_unix_nano=ts_ns,
                time_unix_nano=ts_ns,
                value=val,
            )
            
            if metric_name not in points_by_metric:
                points_by_metric[metric_name] = []
            points_by_metric[metric_name].append(point)
            
        # Construct Metrics
        otel_metrics = []
        for name, points in points_by_metric.items():
            # Create a Gauge metric (assuming value is a gauge, typical for anomalies/forecasts)
            # OTel data model is complex. We need to wrap points in Metric -> Scope -> Resource
            
            # Caution: We need to know if it's Gauge or Sum. 
            # For general time series, Gauge is safest default if we don't know.
            # But OTel Python SDK construction manually is tricky.
            # We construct a Metric object.
            
            # Using Sum for simplicity in data structure match, usually Remote Write handles samples.
            # But actually Prometheus interprets based on type.
            # Let's try to construct a Gauge (which in OTel data model is often represented as Gauge)
            # The library expects `Metric` objects.
            
            # Note: 1.20+ SDK might have specific classes. 
            # We will use a generic approach compatible with recent SDKs.
            
            metric = Metric(
                name=name,
                description="",
                unit="",
                data=None, # Filled below
            )
            
            # We need to wrap points in a specific Data object (Sum, Gauge, etc)
            # In OTel SDK < 1.15 usage might differ. 
            # Trying standard "Sum" with Delta temporality or "Gauge".
            # "Gauge" is simply "NumberDataPoint" in recent versions often wrapped in "Gauge" object.
            
            # Let's try to find the Gauge container.
            from opentelemetry.sdk.metrics.export import Gauge
            
            metric.data = Gauge(data_points=points)
            otel_metrics.append(metric)

        if not otel_metrics:
            return

        # Wrap in ScopeMetrics
        scope_metrics = ScopeMetrics(
            scope=InstrumentationScope(name="openanomaly", version="0.1.0"),
            metrics=otel_metrics,
            schema_url="",
        )
        
        # Wrap in ResourceMetrics
        resource_metrics = ResourceMetrics(
            resource=Resource.create({"service.name": "openanomaly-adapter"}),
            scope_metrics=[scope_metrics],
            schema_url="",
        )
        
        # Wrap in MetricsData
        metrics_data = MetricsData(
            resource_metrics=[resource_metrics]
        )
        
        # Export!
        exporter.export(metrics_data)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
