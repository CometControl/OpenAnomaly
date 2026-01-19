"""
Chronos Adapter - Wrapper for Amazon Chronos Foundation Models.

Uses the 'chronos-forecasting' library to perform zero-shot inference.
"""

import logging
from typing import Any

import pandas as pd
import torch
import numpy as np

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
    Adapter for Amazon Chronos models (chronos-t5-small/base/large, etc.).
    
    Requires 'chronos-forecasting' and 'torch' installed.
    """
    
    def __init__(self, model_id: str, device: str | None = None):
        """
        Initialize Chronos adapter.
        
        Args:
            model_id: HuggingFace model ID (e.g. "amazon/chronos-t5-small")
            device: "cuda", "cpu", or "mps" (auto-detected if None)
        """
        if ChronosPipeline is None:
            raise ImportError(
                "Chronos library not found. Please install with: pip install chronos-forecasting"
            )
            
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.pipeline = None
        self._load_model()
        
    def _load_model(self) -> None:
        """Load the model pipeline."""
        logger.info(f"Loading Chronos model '{self.model_id}' on {self.device}...")
        self.pipeline = ChronosPipeline.from_pretrained(
            self.model_id,
            device_map=self.device,
            torch_dtype=torch.bfloat16,
        )
        
    async def predict(self, df: pd.DataFrame, request: ForecastRequest) -> pd.DataFrame:
        """
        Generate forecast using Chronos.
        """
        if self.pipeline is None:
            self._load_model()
            
        # Context must be a tensor or list. Chronos expects tensor usually for batching,
        # but library handles lists too.
        # context: torch.Tensor of shape (batch_size, context_length)
        # We process single series for now (batch=1).
        
        context_values = torch.tensor(df["y"].values, dtype=torch.float32)
        
        # Predict parameters
        num_samples = request.parameters.get("num_samples", 20)
        temperature = request.parameters.get("temperature", 1.0)
        top_k = request.parameters.get("top_k", 50)
        top_p = request.parameters.get("top_p", 1.0)
        
        # Run inference
        # Returns: tensor (batch_size, num_samples, prediction_length)
        forecast_samples = self.pipeline.predict(
            context=context_values,
            prediction_length=request.prediction_length,
            num_samples=num_samples,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )
        
        # Convert to numpy for quantile calculation
        # Shape: (1, num_samples, horizion) -> (num_samples, horizon)
        samples = forecast_samples[0].numpy()
        
        # Calculate statistics
        median = np.median(samples, axis=0)  # (horizon,)
        
        # Generate future timestamps
        if len(df) >= 2:
            last_dt = df["ds"].iloc[-1]
            prev_dt = df["ds"].iloc[-2]
            freq = last_dt - prev_dt
        else:
            freq = pd.Timedelta("1m") # Default fallback
            
        future_dates = [df["ds"].iloc[-1] + (i + 1) * freq for i in range(len(median))]
        
        # Result DataFrame
        result_df = pd.DataFrame({
            "ds": future_dates,
            "unique_id": df["unique_id"].iloc[0],
            "mean": median,
        })
        
        # Calculate requested quantiles
        for q in request.quantiles:
            # numpy quantile takes q in [0, 1]
            q_values = np.quantile(samples, q, axis=0)
            result_df[f"q_{q}"] = q_values
            
        return result_df
        
    async def health_check(self) -> bool:
        return self.pipeline is not None
