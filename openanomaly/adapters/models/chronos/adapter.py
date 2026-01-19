"""
Chronos Adapter - Wrapper for Amazon Chronos Foundation Models.
"""

import logging
from typing import Any

import pandas as pd
import torch
import numpy as np
from pydantic import PrivateAttr

try:
    from chronos import ChronosPipeline
except ImportError:
    ChronosPipeline = None

from openanomaly.core.ports.model_engine import (
    ForecastRequest,
    ModelEngine,
)

logger = logging.getLogger(__name__)


class ChronosAdapter(ModelEngine):
    """
    Adapter for Amazon Chronos models.
    Configured via Pydantic model fields.
    """
    model_id: str
    device: str = "cpu"  # Default, can be overridden
    
    _pipeline: Any = PrivateAttr(default=None)
    
    def model_post_init(self, __context):
        """Analyze environment for specific defaults or checks."""
        if ChronosPipeline is None:
            raise ImportError(
                "Chronos library not found. Please install with: pip install chronos-forecasting"
            )
        
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
        # Lazy load or eager load? Pydantic approach usually favors config-only on init, 
        # but loading model fits here if we want immediate readiness.
        # Let's keep it lazy for now, or trigger in __init__ via post_init.
        self._load_model()
        
    def _load_model(self) -> None:
        """Load the model pipeline."""
        logger.info(f"Loading Chronos model '{self.model_id}' on {self.device}...")
        self._pipeline = ChronosPipeline.from_pretrained(
            self.model_id,
            device_map=self.device,
            torch_dtype=torch.bfloat16,
        )
        
    async def predict(self, df: pd.DataFrame, request: ForecastRequest) -> pd.DataFrame:
        """Generate forecast using Chronos."""
        if self._pipeline is None:
            self._load_model()
            
        context_values = torch.tensor(df["y"].values, dtype=torch.float32)
        
        num_samples = request.parameters.get("num_samples", 20)
        temperature = request.parameters.get("temperature", 1.0)
        top_k = request.parameters.get("top_k", 50)
        top_p = request.parameters.get("top_p", 1.0)
        
        forecast_samples = self._pipeline.predict(
            context=context_values,
            prediction_length=request.prediction_length,
            num_samples=num_samples,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )
        
        samples = forecast_samples[0].numpy()
        median = np.median(samples, axis=0)
        
        if len(df) >= 2:
            last_dt = df["ds"].iloc[-1]
            prev_dt = df["ds"].iloc[-2]
            freq = last_dt - prev_dt
        else:
            freq = pd.Timedelta("1m")
            
        future_dates = [df["ds"].iloc[-1] + (i + 1) * freq for i in range(len(median))]
        
        result_df = pd.DataFrame({
            "ds": future_dates,
            "unique_id": df["unique_id"].iloc[0],
            "mean": median,
        })
        
        for q in request.quantiles:
            q_values = np.quantile(samples, q, axis=0)
            result_df[f"q_{q}"] = q_values
            
        return result_df
        
    async def health_check(self) -> bool:
        return self._pipeline is not None
