
import os
import asyncio
import logging
from fastapi import FastAPI
from celery import Celery

from openanomaly.adapters.tsdb.prometheus import PrometheusAdapter
from openanomaly.adapters.models.chronos.adapter import ChronosAdapter
from openanomaly.core.services.inference_loop import InferenceLoop
from openanomaly.adapters.config.yaml_store import YamlConfigStore
from openanomaly.adapters.config.settings_loader import load_settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration (Load from YAML with Env Overrides)
settings = load_settings()

REDIS_URL = settings.redis_url
VM_URL = settings.victoriametrics_url
VM_WRITE_URL = settings.get_write_url()

# Celery Application
celery_app = Celery("openanomaly", broker=REDIS_URL, backend=REDIS_URL)

# FastAPI Application
app = FastAPI(title="OpenAnomaly")

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}

@app.post("/pipelines/{pipeline_name}/inference")
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

@app.post("/execute/inference")
async def execute_inference(pipeline: Pipeline):
    """
    Run a stateless ad-hoc inference using the provided pipeline configuration.
    Writes results directly to TSDB.
    """
    # 1. Instantiate Components
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
    
    # 2. Run Inference & Write
    service = InferenceLoop(tsdb, model)
    await service.run_pipeline(pipeline)
    
    return {"status": "success", "message": "Inference executed and results written to TSDB"}

@app.post("/execute/train")
async def execute_training(pipeline: Pipeline):
    """
    Run a stateless ad-hoc training using the provided pipeline configuration.
    Returns the new model ID.
    """
    from openanomaly.core.services.training_loop import TrainingLoop
    
    # 1. Instantiate Components
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
        # Local models training not fully supported in stateless yet, but we allow it
        model = ChronosAdapter(model_id=pipeline.model.id)
            
    tsdb = PrometheusAdapter(read_url=VM_URL, write_url=VM_WRITE_URL)
    
    # 2. Run Training
    service = TrainingLoop(tsdb, model)
    new_id = await service.run_training(pipeline)
    
    return {"status": "success", "model_id": new_id}

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
        config_store = YamlConfigStore(config_path=settings.pipelines_file)
        
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
        config_store = YamlConfigStore(config_path=settings.pipelines_file)
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


        

