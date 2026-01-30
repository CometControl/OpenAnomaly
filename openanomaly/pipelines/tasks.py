
import asyncio
import logging

from celery import shared_task
from django.conf import settings
from openanomaly.config.utils import get_config_store
from openanomaly.common.adapters.tsdb.prometheus import PrometheusAdapter
from openanomaly.pipelines.inference import InferenceLoop
from openanomaly.pipelines.training import TrainingLoop

logger = logging.getLogger(__name__)

# Use settings.PROMETHEUS_URL
PROMETHEUS_URL = settings.PROMETHEUS_URL
# To avoid circular import/logic if get_write_url is needed, we construct it or import it?
# settings.py functions are not importable if they are not in __all__ or if simpler to just reuse logic.
# But settings object doesn't have methods on it like the Pydantic model did.
# So we need to reproduce get_write_url logic or import the function? 
# Importing function from settings.py is bad practice (circular imports).
# We should just inline the logic or use a cached property.
# Simple inline logic:
PROMETHEUS_WRITE_URL = settings.PROMETHEUS_WRITE_URL or f"{PROMETHEUS_URL}/api/v1/write"

@shared_task(name="openanomaly.tasks.run_forecast")
def run_forecast_task(pipeline_name: str):
    """
    Background task to run recurring forecast for a pipeline.
    """
    logger.info(f"Starting FORECAST task for: {pipeline_name}")
    _run_pipeline_action(pipeline_name, "forecast")

@shared_task(name="openanomaly.tasks.run_anomaly_check")
def run_anomaly_task(pipeline_name: str):
    """
    Background task to run recurring anomaly check for a pipeline.
    """
    logger.info(f"Starting ANOMALY CHECK task for: {pipeline_name}")
    _run_pipeline_action(pipeline_name, "anomaly")

# Helper to avoid code duplication
def _run_pipeline_action(pipeline_name: str, action: str):
    async def _execute():
        config_store = get_config_store()
        pipeline = await config_store.get_pipeline(pipeline_name)
        if not pipeline:
            logger.error(f"Pipeline '{pipeline_name}' not found.")
            return

        # Instantiate Model
        if pipeline.model.type == "remote":
            from openanomaly.common.adapters.models.remote import RemoteModelAdapter
            if not pipeline.model.endpoint:
                raise ValueError("Endpoint required for remote model")
            model = RemoteModelAdapter(
                prediction_endpoint=pipeline.model.endpoint,
                serialization_format=pipeline.model.serialization_format,
                **pipeline.model.parameters
            )
        else:
            from openanomaly.common.adapters.models.chronos.adapter import ChronosAdapter
            model = ChronosAdapter(model_id=pipeline.model.id)
        
        # Instantiate TSDB
        prom_url = pipeline.prometheus_url or PROMETHEUS_URL
        prom_write_url = pipeline.prometheus_write_url or PROMETHEUS_WRITE_URL
        tsdb = PrometheusAdapter(read_url=prom_url, write_url=prom_write_url)
        
        # Execute
        service = InferenceLoop(tsdb, model)
        if action == "forecast":
            await service.run_forecast(pipeline)
        elif action == "anomaly":
            await service.run_anomaly_check(pipeline)

    try:
        asyncio.run(_execute())
        return f"{action.upper()} Success: {pipeline_name}"
    except Exception as e:
        logger.error(f"{action} failed: {e}")
        raise e

@shared_task(name="openanomaly.tasks.train_model")
def run_training_task(pipeline_name: str):
    """
    Background task to train model for a specific pipeline.
    """
    logger.info(f"Starting training task for pipeline: {pipeline_name}")
    
    async def _execute():
        config_store = get_config_store()
        pipeline = await config_store.get_pipeline(pipeline_name)
        if not pipeline:
            logger.error(f"Pipeline '{pipeline_name}' not found.")
            return
            
        if pipeline.model.type == "remote":
            from openanomaly.common.adapters.models.remote import RemoteModelAdapter
            if not pipeline.model.endpoint:
                 raise ValueError("Endpoint required for remote model")
            
            training_endpoint = pipeline.training.endpoint if pipeline.training else None
            
            model = RemoteModelAdapter(
                prediction_endpoint=pipeline.model.endpoint,
                training_endpoint=training_endpoint,
                serialization_format=pipeline.model.serialization_format,
                **pipeline.model.parameters
            )
        else:
            from openanomaly.common.adapters.models.chronos.adapter import ChronosAdapter
            model = ChronosAdapter(model_id=pipeline.model.id)
            
        tsdb = PrometheusAdapter(read_url=PROMETHEUS_URL, write_url=PROMETHEUS_WRITE_URL)
        
        service = TrainingLoop(tsdb, model)
        new_id = await service.run_training(pipeline)
        
        if new_id:
            logger.info(f"Pipeline '{pipeline_name}' trained. New Model ID: {new_id}")
            
    try:
        asyncio.run(_execute())
        return f"Training Success: {pipeline_name}"
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise e
