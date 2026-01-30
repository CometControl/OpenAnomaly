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
from typing import TYPE_CHECKING

import pandas as pd
import numpy as np

from openanomaly.common.interfaces.tsdb_client import TSDBClient
from openanomaly.common.dataclasses import ForecastRequest, ForecastResult, AnomalyResult
from openanomaly.common.interfaces.model_engine import ModelEngine

if TYPE_CHECKING:
    from openanomaly.pipelines.models import Pipeline as DjangoPipeline
    from openanomaly.common.dataclasses import Pipeline as PipelineSchema
    
    # Use Union for type hint, assuming duck typing compatibility
    # Both classes have: name, context_window, query, model (with parameters), output (with metric_prefix)
    Pipeline = DjangoPipeline | PipelineSchema

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
        
    async def run_forecast(self, pipeline: Pipeline, now: datetime | None = None) -> None:
        """
        Execute only the forecasting step (Fetch -> Predict -> Write).
        """
        now = now or datetime.utcnow()
        # 1. Generate Forecast
        forecast_df = await self.generate_forecast(pipeline, now)
        if forecast_df.empty:
            return
        # 2. Write Forecast
        await self.write_forecast_results(pipeline, forecast_df)

    async def run_anomaly_check(self, pipeline: Pipeline, now: datetime | None = None) -> None:
        """
        Execute only the anomaly detection step (Fetch forecast & actuals -> Compute Score -> Write).
        """
        now = now or datetime.utcnow()
        # 1. Fetch Actuals and Forecast (from TSDB) for comparison window
        # For simplicity in this iteration, we calculate score based on recent actuals vs PREDICTED values
        # re-generated on the fly (or fetched if we trust TSDB). 
        # Re-generating ensures we use the model's current state.
        
        # Window: Anomaly detection usually looks at the immediate past (e.g., last 15m)
        lookback = self._parse_duration(pipeline.prediction_horizon)
        # Verify against actuals that have just arrived
        
        # TODO: Implement full fetch-from-TSDB comparison. 
        # For now, we reuse generate_forecast for the PAST window to get "what we would have predicted"
        # and compare with "what actually happened".
        
        # ... Implementation placeholder for independent anomaly task ...
        logger.info(f"Running anomaly check for {pipeline.name}")
        pass

    async def generate_forecast(self, pipeline: Pipeline, now: datetime | None = None) -> pd.DataFrame:
        """
        Fetch data and run inference without writing results.
        Returns the forecast DataFrame.
        """
        now = now or datetime.utcnow()
        
        # 1. Calculate Time Windows
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
            return pd.DataFrame()
            
        # 3. Prepare Forecast Request
        horizon_seconds = self._parse_duration(pipeline.prediction_horizon)
        step_seconds = self._parse_duration(pipeline.step)
        prediction_length = int(horizon_seconds / step_seconds)
        
        req = ForecastRequest(
            prediction_length=prediction_length,
            quantiles=[0.1, 0.5, 0.9, 0.95, 0.99], 
            parameters=pipeline.model.parameters,
        )
        
        # 4. Run Inference
        logger.info(f"Running inference for '{pipeline.name}' with model '{pipeline.model.id}'")
        forecast_df = await self.engine.predict(context_df, req)
        
        if forecast_df.empty:
            logger.warning("Model returned no forecast")
            return pd.DataFrame()
            
        return forecast_df

    async def write_forecast_results(self, pipeline: Pipeline, forecast_df: pd.DataFrame) -> None:
        """
        Write forecast results to TSDB.
        """
        output_metrics = []
        source_metric = pipeline.query.split("{")[0].strip()
        base_name = pipeline.output.metric_prefix + pipeline.name
        
        for _, row in forecast_df.iterrows():
            ts = row["ds"]
            
            # Write Mean Forecast
            output_metrics.append({
                "unique_id": f'{base_name}_forecast{{pipeline="{pipeline.name}", source="{source_metric}", type="mean"}}',
                "ds": ts,
                "y": row["mean"]
            })
            
            # Write Quantiles
            for col in forecast_df.columns:
                if col.startswith("q_"):
                    quantile = col.split("_")[1]
                    output_metrics.append({
                        "unique_id": f'{base_name}_forecast{{pipeline="{pipeline.name}", source="{source_metric}", quantile="{quantile}"}}',
                        "ds": ts,
                        "y": row[col]
                    })
        
        if output_metrics:
            logger.info(f"Writing {len(output_metrics)} forecast points to TSDB")
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
