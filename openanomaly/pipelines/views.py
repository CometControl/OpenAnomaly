
import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.conf import settings
from asgiref.sync import async_to_sync

from openanomaly.common.dataclasses import Pipeline
from openanomaly.pipelines.tasks import run_forecast_task, run_anomaly_task, run_training_task
from openanomaly.pipelines.inference import InferenceLoop
from openanomaly.pipelines.training import TrainingLoop
from openanomaly.common.adapters.tsdb.prometheus import PrometheusAdapter

logger = logging.getLogger(__name__)

PROMETHEUS_URL = settings.PROMETHEUS_URL
PROMETHEUS_WRITE_URL = settings.PROMETHEUS_WRITE_URL or f"{PROMETHEUS_URL}/api/v1/write"


class HealthCheckView(APIView):
    """
    Health check endpoint
    """
    @extend_schema(
        summary="Health check",
        description="Returns the API health status and version",
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}, "version": {"type": "string"}}}}
    )
    def post(self, request):
        return Response({"status": "ok", "version": "0.1.0"})


class TriggerForecastView(APIView):
    """
    Trigger forecast run for a pipeline
    """
    @extend_schema(
        summary="Trigger forecast",
        description="Manually trigger a forecast run for a specific pipeline",
        parameters=[OpenApiParameter(name='pipeline_name', type=OpenApiTypes.STR, location=OpenApiParameter.PATH)],
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}, "task_id": {"type": "string"}}}}
    )
    def post(self, request, pipeline_name: str):
        task = run_forecast_task.delay(pipeline_name)
        return Response({"message": "Forecast run triggered", "task_id": str(task.id)})


class TriggerAnomalyCheckView(APIView):
    """
    Trigger anomaly check for a pipeline
    """
    @extend_schema(
        summary="Trigger anomaly check",
        description="Manually trigger an anomaly detection check for a specific pipeline",
        parameters=[OpenApiParameter(name='pipeline_name', type=OpenApiTypes.STR, location=OpenApiParameter.PATH)],
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}, "task_id": {"type": "string"}}}}
    )
    def post(self, request, pipeline_name: str):
        task = run_anomaly_task.delay(pipeline_name)
        return Response({"message": "Anomaly check triggered", "task_id": str(task.id)})


class TriggerTrainingView(APIView):
    """
    Trigger training run for a pipeline
    """
    @extend_schema(
        summary="Trigger training",
        description="Manually trigger a model training run for a specific pipeline",
        parameters=[OpenApiParameter(name='pipeline_name', type=OpenApiTypes.STR, location=OpenApiParameter.PATH)],
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}, "task_id": {"type": "string"}}}}
    )
    def post(self, request, pipeline_name: str):
        task = run_training_task.delay(pipeline_name)
        return Response({"message": "Training run triggered", "task_id": str(task.id)})


class ExecuteInferenceView(APIView):
    """
    Execute stateless inference with custom pipeline configuration
    """
    @extend_schema(
        summary="Execute inference",
        description="Run a stateless ad-hoc inference using the provided pipeline configuration",
        request={"type": "object", "description": "Pipeline configuration object"},
        responses={
            200: {"type": "object", "properties": {"status": {"type": "string"}, "message": {"type": "string"}}},
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
            500: {"type": "object", "properties": {"status": {"type": "string"}, "message": {"type": "string"}}}
        }
    )
    def post(self, request):
        try:
            data = request.data
            from pydantic import TypeAdapter
            pipeline_adapter = TypeAdapter(Pipeline)
            pipeline = pipeline_adapter.validate_python(data)
        except Exception as e:
            return Response({"error": f"Invalid payload: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

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
            prom_write_url = pipeline.prometheus_write_url or  PROMETHEUS_WRITE_URL
            
            tsdb = PrometheusAdapter(read_url=prom_url, write_url=prom_write_url)
            
            # 2. Run Inference & Write
            service = InferenceLoop(tsdb, model)
            await service.run_pipeline(pipeline)
        
        try:
            async_to_sync(_process)()
            return Response({"status": "success", "message": "Inference executed and results written to TSDB"})
        except Exception as e:
            logger.exception("Inference failed")
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExecuteTrainingView(APIView):
    """
    Execute stateless training with custom pipeline configuration
    """
    @extend_schema(
        summary="Execute training",
        description="Run a stateless ad-hoc training using the provided pipeline configuration",
        request={"type": "object", "description": "Pipeline configuration object"},
        responses={
            200: {"type": "object", "properties": {"status": {"type": "string"}, "model_id": {"type": "string"}}},
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
            500: {"type": "object", "properties": {"status": {"type": "string"}, "message": {"type": "string"}}}
        }
    )
    def post(self, request):
        try:
            data = request.data
            from pydantic import TypeAdapter
            pipeline_adapter = TypeAdapter(Pipeline)
            pipeline = pipeline_adapter.validate_python(data)
        except Exception as e:
            return Response({"error": f"Invalid payload: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"status": "success", "model_id": new_id})
        except Exception as e:
            logger.exception("Training failed")
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Export view instances for URL routing
health_check = HealthCheckView.as_view()
trigger_forecast = TriggerForecastView.as_view()
trigger_anomaly_check = TriggerAnomalyCheckView.as_view()
trigger_training = TriggerTrainingView.as_view()
execute_inference_view = ExecuteInferenceView.as_view()
execute_training_view = ExecuteTrainingView.as_view()
