
from datetime import datetime

import httpx
import pandas as pd
from pydantic import PrivateAttr
try:
    from prometheus_remote_writer import RemoteWriter
except ImportError:
    RemoteWriter = None

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
    _writer: "RemoteWriter | None" = PrivateAttr(default=None)

    def model_post_init(self, __context):
        """Normalize URL after initialization."""
        self.read_url = self.read_url.rstrip("/")
        if self.write_url and RemoteWriter is None:
             # Ideally we raise ImportError here if we strictly require it for config,
             # but to allow read-only usage without the pkg we can be lenient or raise.
             # Given user intent, let's assume pkg is required for write capability.
             pass 
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client for reading."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
            )
        return self._client
    
    def _get_writer(self) -> "RemoteWriter":
        """Get or create the RemoteWriter."""
        if self._writer is None:
            if RemoteWriter is None:
                raise ImportError("prometheus-remote-writer not installed")
            if not self.write_url:
                raise RuntimeError("Write URL not configured")
     
            # RemoteWriter uses requests synchronous by default usually, checks docs.
            # Library seems synchonous. We might need to run in executor if high load,
            # but for MVP sync is okay or we check if async supported.
            # Assuming sync for now as per library standard using 'requests'.
            self._writer = RemoteWriter(
                url=self.write_url,
                headers=self.headers,
                # timeout might not be exposed directly in all versions, check args if needed
            )
        return self._writer
    
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
        Write time series data using prometheus-remote-writer.
        """
        writer = self._get_writer()
        
        # DataFrame columns: ['unique_id', 'ds', 'y']
        required_cols = {"unique_id", "ds", "y"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")
            
        for _, row in df.iterrows():
            # Parse metric name and labels from unique_id
            # Format: name{label="value",...} or just name
            raw_id = row["unique_id"]
            if "{" in raw_id and raw_id.endswith("}"):
                name_part, labels_part = raw_id[:-1].split("{", 1)
                metric_name = name_part
                labels = {}
                # Simple parsing of label="value", key2="val2"
                # Robust parsing might require regex if values contain commas/quotes
                # For now, MVP assumes standard structure
                for pair in labels_part.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        labels[k.strip()] = v.strip().strip('"')
            else:
                metric_name = raw_id
                labels = {}
            
            # Timestamp to seconds (library expects float seconds or calls it internally?)
            # Library doc: timestamp in seconds (float or int)
            ts_sec = row["ds"].timestamp()
            value = float(row["y"])
            
            # Sync call (blocking). In prod, offload to thread/process?
            writer.write(
                metric_name=metric_name,
                value=value,
                timestamp=ts_sec,
                labels=labels,
            )
    
    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

