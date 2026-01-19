"""
Prometheus Adapter - TSDB client for Prometheus-compatible databases.

Supports VictoriaMetrics, Thanos, Mimir, Cortex, and native Prometheus.
"""

from datetime import datetime

import httpx
import pandas as pd
from pydantic import PrivateAttr

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

    def model_post_init(self, __context):
        """Normalize URL after initialization."""
        self.read_url = self.read_url.rstrip("/")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
            )
        return self._client
    
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
        """Write time series data using Remote Write."""
        if not self.write_url:
            raise RuntimeError("Write URL not configured")
        
        client = await self._get_client()
        
        required_cols = {"unique_id", "ds", "y"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")
        
        lines = []
        for _, row in df.iterrows():
            metric = row["unique_id"]
            ts_ms = int(row["ds"].timestamp() * 1000)
            val = row["y"]
            lines.append(f"{metric} {val} {ts_ms}")
            
        if not lines:
            return
            
        payload = "\n".join(lines)
        
        response = await client.post(
            self.write_url,
            content=payload,
            headers={"Content-Type": "text/plain"},
        )
        response.raise_for_status()
    
    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
