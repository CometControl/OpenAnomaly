"""
Chronos Adapter - Wrapper for Amazon Chronos-2 Foundation Models.
"""

import logging
from typing import Any

import pandas as pd
import torch
import numpy as np
from pydantic import PrivateAttr

try:
    from chronos import Chronos2Pipeline
except ImportError:
    Chronos2Pipeline = None

from openanomaly.common.dataclasses import ForecastRequest, ForecastResult
from openanomaly.common.interfaces.model_engine import ModelEngine
logger = logging.getLogger(__name__)


class ChronosAdapter(ModelEngine):
    """
    Adapter for Amazon Chronos models (Chronos-2).
    Configured via Pydantic model fields.
    """
    model_id: str
    device: str = "cpu"
    
    _pipeline: Any = PrivateAttr(default=None)
    
    def model_post_init(self, __context):
        """Analyze environment and load model."""
        if Chronos2Pipeline is None:
            raise ImportError(
                "Chronos library not found or outdated. Please install with: pip install chronos-forecasting"
            )
        
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
        self._load_model()
        
    def _load_model(self) -> None:
        """Load the Chronos pipeline."""
        logger.info(f"Loading Chronos model '{self.model_id}' on {self.device}...")
        
        # Use bfloat16 for efficiency on supported hardware, else float32
        torch_dtype = torch.bfloat16 if self.device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
        
        # Simple heuristic: T5 models are V1, others (Bolt, etc) are V2
        if "t5" in self.model_id:
            from chronos import ChronosPipeline
            self._pipeline = ChronosPipeline.from_pretrained(
                self.model_id,
                device_map=self.device,
                torch_dtype=torch_dtype,
            )
            self._is_v1 = True
        else:
            self._pipeline = Chronos2Pipeline.from_pretrained(
                self.model_id,
                device_map=self.device,
                torch_dtype=torch_dtype,
            )
            self._is_v1 = False
        
    async def predict(self, df: pd.DataFrame, request: ForecastRequest) -> pd.DataFrame:
        if self._pipeline is None:
            self._load_model()
            
        required_cols = {"unique_id", "ds", "y"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"Input DataFrame must contain columns: {required_cols}")
            
        if not pd.api.types.is_datetime64_any_dtype(df["ds"]):
             df["ds"] = pd.to_datetime(df["ds"])

        # V1 (T5) Logic
        if getattr(self, "_is_v1", False):
            # Sort by ds to ensure time content is ordered
            df = df.sort_values("ds")
            context_tensor = torch.tensor(df["y"].values, dtype=torch.float32)
            
            # Predict
            # Chronos V1 predict returns a Generator or Tensor depending on usage.
            # default: returns (batch_size, num_samples, prediction_length)
            forecast = self._pipeline.predict(
                context_tensor,
                prediction_length=request.prediction_length,
                num_samples=20, # Default samples for distribution
                limit_prediction_length=False
            )
            
            # Forecast shape: [1, num_samples, horzion] since we pass 1 series
            # Quantiles calculation
            low_q = np.quantile(forecast[0].numpy(), q=0.1, axis=0)
            median_q = np.quantile(forecast[0].numpy(), q=0.5, axis=0)
            high_q = np.quantile(forecast[0].numpy(), q=0.9, axis=0)
            mean_q = np.mean(forecast[0].numpy(), axis=0)
            
            # Construct Result DF
            # Generate future timestamps
            last_date = df["ds"].iloc[-1]
            # Infer frequency if possible, else assume 1m or use request
            # For now, simplistic: add 1 unit per step? No, we need freq.
            # Since pipeline doesn't enforce freq, we rely on caller or infer.
            freq = pd.infer_freq(df["ds"]) or "T" # Minutely default
            future_dates = pd.date_range(start=last_date, periods=request.prediction_length + 1, freq=freq)[1:]
            
            forecast_df = pd.DataFrame({
                "unique_id": df["unique_id"].iloc[0],
                "ds": future_dates,
                "mean": mean_q,
                "q_0.1": low_q,
                "q_0.5": median_q,
                "q_0.9": high_q
            })
            return forecast_df

        # V2 (Chronos2/Bolt) Logic - use predict_df
        try:
            forecast_df = self._pipeline.predict_df(
                df,
                prediction_length=request.prediction_length,
                quantile_levels=request.quantiles,
                id_column="unique_id",
                timestamp_column="ds",
                target="y",
            )
        except Exception as e:
            logger.error(f"Chronos prediction failed: {e}")
            raise RuntimeError(f"Model prediction error: {e}") from e
            
        # Post-process V2 Output
        rename_map = {}
        for q in request.quantiles:
            col_name = str(q)
            if col_name in forecast_df.columns:
                rename_map[col_name] = f"q_{q}"
        
        if rename_map:
            forecast_df = forecast_df.rename(columns=rename_map)
            
        if "mean" not in forecast_df.columns and "q_0.5" in forecast_df.columns:
            forecast_df["mean"] = forecast_df["q_0.5"]
            
        return forecast_df
        
    async def train(
        self,
        df: pd.DataFrame,
        parameters: dict[str, Any]
    ) -> str:
        """
        Train the model.
        Chronos is a pre-trained foundation model. 
        Returns the current model_id as it doesn't require training.
        """
        logger.info(f"Skipping training for pre-trained model '{self.model_id}'")
        return self.model_id
        
    async def health_check(self) -> bool:
        return self._pipeline is not None
