"""
Remote Model Adapter - HTTP client for external inference endpoints.

This adapter calls external model servers that implement the standard
inference API contract defined in the technical design.
"""

import httpx

import pandas as pd

from openanomaly.core.ports.model_engine import (
    ForecastRequest,
    ModelEngine,
)


class RemoteModelAdapter(ModelEngine):
    """
    Model adapter that calls external inference endpoints via HTTP.
    
    The remote server must implement the following contract:
    
    POST /predict
    Request:
        {
            "context": [1.2, 3.4, ...],
            "prediction_length": 12,
            "quantiles": [0.1, 0.5, 0.9]
        }
    Response:
        {
            "forecast": [7.8, 9.0, ...],
            "quantiles": {...}
        }
    """
    
    def __init__(
        self,
        endpoint: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ):
        """
        Initialize the remote model adapter.
        
        Args:
            endpoint: Base URL of the inference server
            timeout: Request timeout in seconds
            headers: Optional headers (e.g., for authentication)
        """
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
            )
        return self._client
    
    async def predict(self, df: pd.DataFrame, request: ForecastRequest) -> pd.DataFrame:
        """
        Call the remote inference endpoint.
        """
        client = await self._get_client()
        
        # Extract context (assuming single series or batch logic handled by remote)
        # For this MVP, we assume the remote endpoint expects a single series "context" list.
        # In a real batch scenario, we would send a list of contexts.
        context_values = df["y"].tolist()
        
        # Serialize request
        payload = request.model_dump(mode="json")
        payload["context"] = context_values
        
        response = await client.post(
            f"{self.endpoint}/predict",
            json=payload,
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Reconstruct DataFrame from response
        # Assume response structure: 
        # { "mean": [...], "quantiles": {"0.1": [...], ...} } or legacy { "forecast": [...] }
        
        forecast_values = data.get("mean") or data.get("forecast") or []
        quantiles = data.get("quantiles", {})
        
        if not forecast_values:
            return pd.DataFrame()
            
        # Generate future timestamps
        # Infer frequency from last 2 points of input
        if len(df) >= 2:
            last_dt = df["ds"].iloc[-1]
            prev_dt = df["ds"].iloc[-2]
            freq = last_dt - prev_dt
        else:
            # Fallback or error? Assume 1m?
            # Ideally freq should be passed.
            raise ValueError("Input context too short to infer frequency")
            
        future_dates = [df["ds"].iloc[-1] + (i + 1) * freq for i in range(len(forecast_values))]
        
        result_df = pd.DataFrame({
            "ds": future_dates,
            "unique_id": df["unique_id"].iloc[0] if not df.empty else "unknown",
            "mean": forecast_values,
        })
        
        # Add quantiles
        for q_key, q_vals in quantiles.items():
            result_df[f"q_{q_key}"] = q_vals
            
        return result_df
    
    async def health_check(self) -> bool:
        """
        Check if the remote server is healthy.
        
        Returns:
            True if server responds to /health, False otherwise
        """
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
