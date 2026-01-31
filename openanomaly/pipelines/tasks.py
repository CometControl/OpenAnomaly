
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
        
        # Initialize Kafka producer if enabled
        kafka_producer = None
        if pipeline.training and pipeline.training.kafka_enabled:
            from openanomaly.common.adapters.kafka_producer import KafkaProducerAdapter
            try:
                kafka_producer = KafkaProducerAdapter(
                    bootstrap_servers=pipeline.training.kafka_bootstrap_servers
                )
                logger.info(f"Kafka producer initialized for topic '{pipeline.training.kafka_topic}'")
            except Exception as e:
                logger.warning(f"Failed to initialize Kafka producer: {e}. Continuing without Kafka.")
                kafka_producer = None
        
        # Helper to build message from template
        def build_kafka_message(event_type: str, **context):
            """Build message from template with context variables."""
            if not pipeline.training.kafka_message_template:
                # Default message structure if no template defined
                from datetime import datetime
                return {
                    "event_type": event_type,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "pipeline_name": pipeline_name,
                    **context
                }
            
            # Use custom template and substitute variables
            message = {}
            for key, value_template in pipeline.training.kafka_message_template.items():
                if isinstance(value_template, str):
                    # Simple string template substitution
                    message[key] = value_template.format(
                        event_type=event_type,
                        pipeline_name=pipeline_name,
                        **context
                    )
                else:
                    # Use value as-is for non-string types
                    message[key] = value_template
            
            # Add any context variables not in template
            for key, value in context.items():
                if key not in message:
                    message[key] = value
            
            return message
        
        # Build message key from template
        message_key = pipeline.training.kafka_message_key.format(pipeline_name=pipeline_name) if pipeline.training else None
        
        # Publish training started event
        if kafka_producer:
            message = build_kafka_message(
                event_type="training_started",
                model_id=pipeline.model.id,
                training_window=pipeline.training.window if pipeline.training else None,
            )
            kafka_producer.publish_message(
                topic=pipeline.training.kafka_topic,
                message=message,
                key=message_key
            )
            
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
        
        # Track training metrics
        import time
        start_time = time.time()
        
        try:
            new_id = await service.run_training(pipeline)
            
            duration = time.time() - start_time
            
            if new_id:
                logger.info(f"Pipeline '{pipeline_name}' trained. New Model ID: {new_id}")
                
                # Publish training completed event
                if kafka_producer:
                    message = build_kafka_message(
                        event_type="training_completed",
                        model_id=new_id,
                        training_window=pipeline.training.window if pipeline.training else None,
                        status="success",
                        duration_seconds=round(duration, 2),
                    )
                    kafka_producer.publish_message(
                        topic=pipeline.training.kafka_topic,
                        message=message,
                        key=message_key
                    )
                    kafka_producer.flush()
                    
        except Exception as e:
            duration = time.time() - start_time
            
            # Publish training failed event
            if kafka_producer:
                message = build_kafka_message(
                    event_type="training_failed",
                    model_id=pipeline.model.id,
                    training_window=pipeline.training.window if pipeline.training else None,
                    status="failed",
                    duration_seconds=round(duration, 2),
                    error=str(e)
                )
                kafka_producer.publish_message(
                    topic=pipeline.training.kafka_topic,
                    message=message,
                    key=message_key
                )
                kafka_producer.flush()
            raise
        finally:
            # Clean up Kafka producer
            if kafka_producer:
                kafka_producer.close()
            
    try:
        asyncio.run(_execute())
        return f"Training Success: {pipeline_name}"
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise e



@shared_task(name="openanomaly.tasks.simulate_work")
def simulate_work(task_id: int):
    """
    Simulate a long running task to test worker scalibility.
    """
    import time
    import socket
    import random
    duration = random.randint(3, 8)
    worker_name = socket.gethostname()
    logger.info(f"[Task {task_id}] Started on {worker_name}. Sleeping for {duration}s...")
    time.sleep(duration)
    logger.info(f"[Task {task_id}] Finished on {worker_name}.")
    return {"task_id": task_id, "worker": worker_name, "duration": duration}

@shared_task(name="openanomaly.tasks.heartbeat")
def heartbeat_task(timestamp: float):
    """
    Simple task to test scheduler HA.
    Increments a counter in Redis to verify unique execution.
    """
    import redis
    import os
    
    # Simple redis connection (or use settings)
    redis_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
    # If connection fails, task fails, which is fine for testing
    r = redis.from_url(redis_url)
    
    # Increment counter
    count = r.incr("scheduler:heartbeat:count")
    logger.info(f"Heartbeat {timestamp} processed. Count: {count}")
    return count
