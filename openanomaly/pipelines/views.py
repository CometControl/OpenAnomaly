
import json
import logging
from django.http import JsonResponse, HttpRequest
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from asgiref.sync import async_to_sync

from openanomaly.common.dataclasses import Pipeline
from openanomaly.pipelines.tasks import run_forecast_task, run_anomaly_task, run_training_task
from openanomaly.pipelines.inference import InferenceLoop
from openanomaly.pipelines.training import TrainingLoop
from openanomaly.common.adapters.tsdb.prometheus import PrometheusAdapter

logger = logging.getLogger(__name__)

PROMETHEUS_URL = settings.PROMETHEUS_URL
PROMETHEUS_WRITE_URL = settings.PROMETHEUS_WRITE_URL or f"{PROMETHEUS_URL}/api/v1/write"

@csrf_exempt
@require_POST
def health_check(request: HttpRequest):
    return JsonResponse({"status": "ok", "version": "0.1.0"})

@csrf_exempt
@require_POST
def trigger_forecast(request: HttpRequest, pipeline_name: str):
    """
    Manually trigger a forecast run for a pipeline.
    POST /pipelines/{pipeline_name}/forecast
    """
    task = run_forecast_task.delay(pipeline_name)
    return JsonResponse({"message": "Forecast run triggered", "task_id": str(task.id)})

@csrf_exempt
@require_POST
def trigger_anomaly_check(request: HttpRequest, pipeline_name: str):
    """
    Manually trigger an anomaly check for a pipeline.
    POST /pipelines/{pipeline_name}/anomaly
    """
    task = run_anomaly_task.delay(pipeline_name)
    return JsonResponse({"message": "Anomaly check triggered", "task_id": str(task.id)})

@csrf_exempt
@require_POST
def trigger_training(request: HttpRequest, pipeline_name: str):
    """
    Manually trigger a training run for a pipeline.
    POST /pipelines/{pipeline_name}/train
    """
    task = run_training_task.delay(pipeline_name)
    return JsonResponse({"message": "Training run triggered", "task_id": str(task.id)})

@csrf_exempt
@require_POST
def execute_inference_view(request: HttpRequest):
    """
    Run a stateless ad-hoc inference using the provided pipeline configuration.
    POST /execute/inference
    """
    try:
        data = json.loads(request.body)
        # Using dacite or simple init if structure matches perfectly
        # For robustness in production, install dacite or use DRF serializers.
        # Fallback to direct init (assumes proper structure for now)
        # Or re-use pydantic TypeAdapter just for validation if desired
        from pydantic import TypeAdapter
        pipeline_adapter = TypeAdapter(Pipeline)
        pipeline = pipeline_adapter.validate_python(data)
    except Exception as e:
        return JsonResponse({"error": f"Invalid payload: {str(e)}"}, status=400)

    async def _process():
        # 1. Instantiate Components
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
        
        prom_url = pipeline.prometheus_url or PROMETHEUS_URL
        prom_write_url = pipeline.prometheus_write_url or PROMETHEUS_WRITE_URL
        
        tsdb = PrometheusAdapter(read_url=prom_url, write_url=prom_write_url)
        
        # 2. Run Inference & Write
        service = InferenceLoop(tsdb, model)
        await service.run_pipeline(pipeline)
    
    try:
        async_to_sync(_process)()
        return JsonResponse({"status": "success", "message": "Inference executed and results written to TSDB"})
    except Exception as e:
        logger.exception("Inference failed")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_POST
def execute_training_view(request: HttpRequest):
    """
    Run a stateless ad-hoc training using the provided pipeline configuration.
    POST /execute/train
    """
    try:
        data = json.loads(request.body)
        from pydantic import TypeAdapter
        pipeline_adapter = TypeAdapter(Pipeline)
        pipeline = pipeline_adapter.validate_python(data)
    except Exception as e:
        return JsonResponse({"error": f"Invalid payload: {str(e)}"}, status=400)

    async def _process():
        # 1. Instantiate Components
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
        
        # 2. Run Training
        service = TrainingLoop(tsdb, model)
        return await service.run_training(pipeline)

    try:
        new_id = async_to_sync(_process)()
        return JsonResponse({"status": "success", "model_id": new_id})
    except Exception as e:
        logger.exception("Training failed")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
