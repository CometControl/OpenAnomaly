
import json
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.conf import settings
from asgiref.sync import async_to_sync

from openanomaly.pipelines.models import Pipeline
from openanomaly.pipelines.serializers import PipelineSerializer
from openanomaly.common.dataclasses import Pipeline as PipelineDataclass
from openanomaly.pipelines.tasks import run_forecast_task, run_anomaly_task, run_training_task
from openanomaly.pipelines.inference import InferenceLoop
from openanomaly.pipelines.training import TrainingLoop
from openanomaly.common.adapters.tsdb.prometheus import PrometheusAdapter

logger = logging.getLogger(__name__)

PROMETHEUS_URL = settings.PROMETHEUS_URL
PROMETHEUS_WRITE_URL = settings.PROMETHEUS_WRITE_URL or f"{PROMETHEUS_URL}/api/v1/write"


class PipelineViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Pipeline CRUD operations.
    
    Provides:
    - GET /pipelines/ - List all pipelines
    - POST /pipelines/ - Create new pipeline
    - GET /pipelines/{id}/ - Get pipeline details
    - PUT /pipelines/{id}/ - Update pipeline (full)
    - PATCH /pipelines/{id}/ - Update pipeline (partial)
    - DELETE /pipelines/{id}/ - Delete pipeline
    
    Custom actions:
    - POST /pipelines/{id}/trigger_forecast/ - Trigger forecast task
    - POST /pipelines/{id}/trigger_anomaly/ - Trigger anomaly detection task
    - POST /pipelines/{id}/trigger_training/ - Trigger training task
    """
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer
    
    @extend_schema(
        summary="Trigger forecast for this pipeline",
        description="Manually trigger a forecast run for this specific pipeline",
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}, "task_id": {"type": "string"}}}}
    )
    @action(detail=True, methods=['post'])
    def trigger_forecast(self, request, pk=None):
        """Trigger forecast task for this pipeline"""
        pipeline = self.get_object()
        task = run_forecast_task.delay(pipeline.name)
        return Response({"message": "Forecast run triggered", "task_id": str(task.id)})
    
    @extend_schema(
        summary="Trigger anomaly detection for this pipeline",
        description="Manually trigger anomaly detection for this specific pipeline",
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}, "task_id": {"type": "string"}}}}
    )
    @action(detail=True, methods=['post'])
    def trigger_anomaly(self, request, pk=None):
        """Trigger anomaly detection task for this pipeline"""
        pipeline = self.get_object()
        task = run_anomaly_task.delay(pipeline.name)
        return Response({"message": "Anomaly check triggered", "task_id": str(task.id)})
    
    @extend_schema(
        summary="Trigger training for this pipeline",
        description="Manually trigger model training for this specific pipeline",
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}, "task_id": {"type": "string"}}}}
    )
    @action(detail=True, methods=['post'])
    def trigger_training(self, request, pk=None):
        """Trigger training task for this pipeline"""
        pipeline = self.get_object()
        task = run_training_task.delay(pipeline.name)
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
            pipeline_adapter = TypeAdapter(PipelineDataclass)
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
            prom_write_url = pipeline.prometheus_write_url or PROMETHEUS_WRITE_URL
            
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
            pipeline_adapter = TypeAdapter(PipelineDataclass)
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
