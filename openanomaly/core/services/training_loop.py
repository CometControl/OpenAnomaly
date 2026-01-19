"""
Training Loop Service - Orchestrates the model training process.
"""

import logging
import pandas as pd
from datetime import timedelta

from openanomaly.core.ports.tsdb_client import TSDBClient
from openanomaly.core.ports.model_engine import ModelEngine
from openanomaly.core.domain.pipeline import Pipeline

logger = logging.getLogger(__name__)


class TrainingLoop:
    """
    Service to run the training loop for a specific pipeline.
    """
    
    def __init__(self, tsdb: TSDBClient, model: ModelEngine):
        self.tsdb = tsdb
        self.model = model
        
    async def run_training(self, pipeline: Pipeline) -> str | None:
        """
        Execute the training pipeline.
        
        Args:
            pipeline: Pipeline configuration
            
        Returns:
            str: New Model ID/Artifact URI if successful, None otherwise.
        """
        if not pipeline.training or not pipeline.training.enabled:
            logger.info(f"Training disabled for pipeline '{pipeline.name}'")
            return None
            
        logger.info(f"Starting training for pipeline '{pipeline.name}'")
        
        # 1. Determine Time Window
        # Parse window string (e.g. "30d") to timedelta
        # Simple parser for now (d=days, h=hours, m=minutes)
        window_str = pipeline.training.window
        if window_str.endswith("d"):
            window_delta = timedelta(days=int(window_str[:-1]))
        elif window_str.endswith("h"):
            window_delta = timedelta(hours=int(window_str[:-1]))
        else:
            window_delta = timedelta(days=30) # Default
            
        end_time = pd.Timestamp.now(tz="UTC")
        start_time = end_time - window_delta
        
        # 2. Fetch Training Data
        logger.info(f"Fetching training data from {start_time} to {end_time}")
        history_df = self.tsdb.read_series(
            query=pipeline.query,
            start=start_time,
            end=end_time,
            step=pipeline.step
        )
        
        if history_df.empty:
            logger.warning(f"No training data found for {pipeline.name}")
            return None
            
        logger.info(f"Fetched {len(history_df)} points for training.")
        
        # 3. Train Model
        logger.info(f"Training model '{pipeline.model.id}'...")
        try:
            new_model_id = await self.model.train(
                df=history_df,
                parameters=pipeline.training.parameters
            )
            logger.info(f"Training complete. Artifact: {new_model_id}")
            return new_model_id
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise e
