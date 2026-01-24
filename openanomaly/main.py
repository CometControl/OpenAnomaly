
import os
import asyncio
import logging
from fastapi import FastAPI
from celery import Celery

from openanomaly.adapters.tsdb.prometheus import PrometheusAdapter
from openanomaly.adapters.models.chronos.adapter import ChronosAdapter
from openanomaly.core.services.inference_loop import InferenceLoop
from openanomaly.adapters.config.yaml_store import YamlConfigStore

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
VM_URL = os.getenv("VICTORIAMETRICS_URL", "http://localhost:8428")
# VM write path for prometheus remote write is usually /api/v1/write
VM_WRITE_URL = os.getenv("VICTORIAMETRICS_WRITE_URL", f"{VM_URL}/api/v1/write")

# Celery Application
celery_app = Celery("openanomaly", broker=REDIS_URL, backend=REDIS_URL)

# FastAPI Application
app = FastAPI(title="OpenAnomaly")

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}

@app.post("/pipelines/{pipeline_name}/trigger")
def trigger_inference(pipeline_name: str):
    """
    Manually trigger an inference run for a pipeline.
    """
    # Dispatch task asynchronously
    task = run_inference_task.delay(pipeline_name)
    return {"message": "Inference run triggered", "task_id": str(task.id)}

@app.post("/pipelines/{pipeline_name}/train")
def trigger_training(pipeline_name: str):
    """
    Manually trigger a training run for a pipeline.
    """
    # Dispatch task asynchronously
    task = run_training_task.delay(pipeline_name)
    return {"message": "Training run triggered", "task_id": str(task.id)}

@app.post("/execute/forecast")
async def execute_forecast(pipeline: Pipeline):
    """
    Run a stateless ad-hoc forecast using the provided pipeline configuration.
    Returns the forecast result directly without saving context.
    """
    # 1. Instantiate Components
    # TODO: Refactor component instantiation into a reusable factory/dependency injection
    if pipeline.model.type == "remote":
        from openanomaly.adapters.models.remote import RemoteModelAdapter
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
        model = ChronosAdapter(model_id=pipeline.model.id)
    
    tsdb = PrometheusAdapter(read_url=VM_URL, write_url=VM_WRITE_URL)
    
    # 2. Run Inference
    service = InferenceLoop(tsdb, model)
    forecast_df = await service.generate_forecast(pipeline)
    
    # 3. Serialize Result
    # Return as JSON records for simplicity/API compatibility
    if forecast_df.empty:
        return {"data": []}
        
    return {
        "data": forecast_df.to_dict(orient="records"),
        "meta": {
            "rows": len(forecast_df),
            "columns": list(forecast_df.columns)
        }
    }

# Celery Tasks
@celery_app.task(name="openanomaly.tasks.run_inference")
def run_inference_task(pipeline_name: str):
    """
    Background task to run inference for a specific pipeline.
    """
    logger.info(f"Starting inference task for pipeline: {pipeline_name}")
    
    async def _execute():
        # 1. Load Pipeline Configuration
        # Assuming pipelines.yaml is in the current working directory
        config_store = YamlConfigStore(config_path="pipelines.yaml")
        
        # Load pipeline to get model config
        pipeline = await config_store.get_pipeline(pipeline_name)
        if not pipeline:
            logger.error(f"Pipeline '{pipeline_name}' not found in configuration.")
            return

        # 2. Instantiate Components based on Pipeline Config
        logger.info(f"Initializing model '{pipeline.model.id}' for pipeline '{pipeline_name}'")
        
        if pipeline.model.type == "remote":
            from openanomaly.adapters.models.remote import RemoteModelAdapter
            # Ensure prediction endpoint is provided (mapped from model.endpoint)
            if not pipeline.model.endpoint:
                raise ValueError("Endpoint required for remote model")
            
            # Use model.endpoint as prediction_endpoint
            model = RemoteModelAdapter(
                prediction_endpoint=pipeline.model.endpoint,
                serialization_format=pipeline.model.serialization_format,
                **pipeline.model.parameters
            )
        else:
            model = ChronosAdapter(model_id=pipeline.model.id)
        
        # TSDB is currently environment-based (shared infra)
        tsdb = PrometheusAdapter(read_url=VM_URL, write_url=VM_WRITE_URL)
        
        # 3. Service Execution
        service = InferenceLoop(tsdb, model)
        await service.run_pipeline(pipeline)

    try:
        asyncio.run(_execute())
        return f"Success: {pipeline_name}"
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise e

@celery_app.task(name="openanomaly.tasks.train_model")
def run_training_task(pipeline_name: str):
    """
    Background task to train model for a specific pipeline.
    """
    import asyncio
    from openanomaly.core.services.training_loop import TrainingLoop
    
    logger.info(f"Starting training task for pipeline: {pipeline_name}")
    
    async def _execute():
        # 1. Load Pipeline Configuration
        config_store = YamlConfigStore(config_path="pipelines.yaml")
        pipeline = await config_store.get_pipeline(pipeline_name)
        if not pipeline:
            logger.error(f"Pipeline '{pipeline_name}' not found.")
            return
            
        # 2. Instantiate Components
        if pipeline.model.type == "remote":
            from openanomaly.adapters.models.remote import RemoteModelAdapter
            if not pipeline.model.endpoint:
                 raise ValueError("Endpoint required for remote model")
            
            # Pass both endpoints
            training_endpoint = pipeline.training.endpoint if pipeline.training else None
            
            model = RemoteModelAdapter(
                prediction_endpoint=pipeline.model.endpoint,
                training_endpoint=training_endpoint,
                serialization_format=pipeline.model.serialization_format,
                **pipeline.model.parameters
            )
        else:
            # Local models (Chronos) generally don't support training via this task yet
            # But we instantiate anyway to allow the adapter to handle it (e.g. log skip)
            model = ChronosAdapter(model_id=pipeline.model.id)
            
        tsdb = PrometheusAdapter(read_url=VM_URL, write_url=VM_WRITE_URL)
        
        # 3. Service Execution
        service = TrainingLoop(tsdb, model)
        new_id = await service.run_training(pipeline)
        
        if new_id:
            logger.info(f"Pipeline '{pipeline_name}' trained. New Model ID: {new_id}")
            # TODO: Update pipeline config with new model ID if needed
            
    try:
        asyncio.run(_execute())
        return f"Training Success: {pipeline_name}"
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise e


        

