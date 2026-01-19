"""
Remote Model Adapter - HTTP client for external inference endpoints.
"""

import httpx
import pandas as pd
from pydantic import PrivateAttr

from openanomaly.core.ports.model_engine import (
    ForecastRequest,
    ModelEngine,
)


class RemoteModelAdapter(ModelEngine):
    """
    Model adapter that calls external inference endpoints via HTTP.
    Configured via Pydantic model fields.
    """
    endpoint: str
    timeout: float = 30.0
    headers: dict[str, str] = {}
    
    _client: httpx.AsyncClient | None = PrivateAttr(default=None)
    
    def model_post_init(self, __context):
        self.endpoint = self.endpoint.rstrip("/")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
            )
        return self._client
    
    async def predict(self, df: pd.DataFrame, request: ForecastRequest) -> pd.DataFrame:
        """Call the remote inference endpoint."""
        client = await self._get_client()
        
        context_values = df["y"].tolist()
        
        payload = request.model_dump(mode="json")
        payload["context"] = context_values
        
        response = await client.post(
            f"{self.endpoint}/predict",
            json=payload,
        )
        response.raise_for_status()
        
        data = response.json()
        
        forecast_values = data.get("mean") or data.get("forecast") or []
        quantiles = data.get("quantiles", {})
        
        if not forecast_values:
            return pd.DataFrame()
            
        if len(df) >= 2:
            last_dt = df["ds"].iloc[-1]
            prev_dt = df["ds"].iloc[-2]
            freq = last_dt - prev_dt
        else:
            raise ValueError("Input context too short to infer frequency")
            
        future_dates = [df["ds"].iloc[-1] + (i + 1) * freq for i in range(len(forecast_values))]
        
        result_df = pd.DataFrame({
            "ds": future_dates,
            "unique_id": df["unique_id"].iloc[0] if not df.empty else "unknown",
            "mean": forecast_values,
        })
        
        for q_key, q_vals in quantiles.items():
            result_df[f"q_{q_key}"] = q_vals
            
        return result_df
    
    async def train(
        self,
        df: pd.DataFrame,
        parameters: dict[str, Any]
    ) -> str:
        """Call the remote training endpoint."""
        import json
        client = await self._get_client()
        
        # Serialize DataFrame safely
        data_json = df.to_json(orient="records", date_format="iso")
        data_list = json.loads(data_json)
        
        payload = {
            "data": data_list,
            "parameters": parameters
        }
        
        response = await client.post(
            f"{self.endpoint}/train",
            json=payload,
        )
        response.raise_for_status()
        
        # Expecting {"model_id": "..."} or {"artifact_uri": "..."}
        data = response.json()
        model_id = data.get("model_id") or data.get("artifact_uri")
        
        if not model_id:
            raise ValueError("Remote training response missing 'model_id' or 'artifact_uri'")
            
        return str(model_id)

    async def health_check(self) -> bool:
        """Check if the remote server is healthy."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.endpoint}/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
