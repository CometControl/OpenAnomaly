"""
Inference Loop Service - The core engine of OpenAnomaly.

This service orchestrates the fetch-predict-write cycle:
1. Fetch data from TSDB (Context)
2. Run Model Inference (Zero-Shot)
3. Calculate Anomaly Scores
4. Write results back to TSDB
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from openanomaly.core.domain.pipeline import Pipeline
from openanomaly.core.ports.model_engine import ForecastRequest, ModelEngine
from openanomaly.core.ports.tsdb_client import TSDBClient

logger = logging.getLogger(__name__)


class InferenceLoop:
    """
    Core service that executes a single inference iteration for a pipeline.
    """
    
    def __init__(
        self,
        tsdb: TSDBClient,
        engine: ModelEngine,
    ):
        """
        Initialize the inference loop.
        
        Args:
            tsdb: Port to read/write time series
            engine: Port to run forecasting model
        """
        self.tsdb = tsdb
        self.engine = engine
        
    async def run_pipeline(self, pipeline: Pipeline, now: datetime | None = None) -> None:
        """
        Execute the pipeline logic.
        
        Args:
            pipeline: Pipeline configuration
            now: Current timestamp (default: utcnow)
        """
        now = now or datetime.utcnow()
        
        # 1. Calculate Time Windows
        # Parse context_window (e.g. "1h") - simplistic parsing for MVP
        # In prod use a proper duration parser
        window_seconds = self._parse_duration(pipeline.context_window)
        start_time = now - timedelta(seconds=window_seconds)
        
        # 2. Fetch Context Data
        logger.info(f"Fetching data for '{pipeline.name}' start={start_time} end={now}")
        context_df = await self.tsdb.query_range(
            query=pipeline.query,
            start=start_time,
            end=now,
            step=pipeline.step,
        )
        
        if context_df.empty:
            logger.warning(f"No data found for pipeline '{pipeline.name}'")
            return
            
        # 3. Prepare Forecast Request
        # Parse prediction horizon
        horizon_seconds = self._parse_duration(pipeline.prediction_horizon)
        # Calculate horizon steps based on step size (simplistic)
        step_seconds = self._parse_duration(pipeline.step)
        prediction_length = int(horizon_seconds / step_seconds)
        
        req = ForecastRequest(
            prediction_length=prediction_length,
            quantiles=[0.1, 0.5, 0.9, 0.95, 0.99], # Default set or from config
            parameters=pipeline.model.parameters,
        )
        
        # 4. Run Inference (Zero-Shot)
        # Note: If DF has multiple series (unique_ids), ModelEngine should handle it 
        # or we loop here. Our ModelEngine definition supports DF with multiple unique_ids
        # natively if batched, but ChronosAdapter example handled one. 
        # Let's assume Adapter handles the DF.
        logger.info(f"Running inference for '{pipeline.name}' with model '{pipeline.model.id}'")
        forecast_df = await self.engine.predict(context_df, req)
        
        if forecast_df.empty:
            logger.warning("Model returned no forecast")
            return
            
        # 5. Score Anomalies (Optional / Future Phase logic)
        # basic z-score or IQR based on quantiles
        # For now, we write the forecast mean and bounds.
        
        # 6. Write Results
        # Remote Write expects "unique_id", "ds", "y"
        # We rename columns to write back metrics
        
        output_metrics = []
        
        for _, row in forecast_df.iterrows():
            # Base metric name
            base_name = pipeline.output.metric_prefix + pipeline.name
            ts = row["ds"]
            
            # Write Mean Forecast
            output_metrics.append({
                "unique_id": f'{base_name}_forecast{{pipeline="{pipeline.name}", type="mean"}}',
                "ds": ts,
                "y": row["mean"]
            })
            
            # Write Quantiles
            for col in forecast_df.columns:
                if col.startswith("q_"):
                    quantile = col.split("_")[1]
                    output_metrics.append({
                        "unique_id": f'{base_name}_forecast{{pipeline="{pipeline.name}", quantile="{quantile}"}}',
                        "ds": ts,
                        "y": row[col]
                    })
        
        if output_metrics:
            logger.info(f"Writing {len(output_metrics)} result points to TSDB")
            metrics_df = pd.DataFrame(output_metrics)
            await self.tsdb.write(metrics_df)
            
    def _parse_duration(self, duration_str: str) -> int:
        """Parse Prometheus-style duration string to seconds."""
        # Simple parser: 1h, 5m, 30s
        unit = duration_str[-1]
        value = int(duration_str[:-1])
        if unit == "s": return value
        if unit == "m": return value * 60
        if unit == "h": return value * 3600
        if unit == "d": return value * 86400
        return value
