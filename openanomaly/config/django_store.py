
import logging
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from openanomaly.common.interfaces.config_store import ConfigStore
from openanomaly.common.dataclasses import Pipeline as PipelineData
from openanomaly.pipelines.models import Pipeline as PipelineModel

logger = logging.getLogger(__name__)

class DjangoConfigStore(ConfigStore):
    """
    Django ORM implementation of ConfigStore.
    Works with any database supported by Django (MongoDB, SQLite, Postgres, etc).
    """
    
    async def get_pipeline(self, name: str) -> PipelineData | None:
        """
        Retrieve a pipeline configuration by name.
        """
        try:
            # We use sync_to_async because Django ORM is synchronous (mostly)
            # although recent Django has async interface, typical usage is wrapper for safety
            # PipelineModel.objects.get matches DB record.
            
            # The PipelineModel has @properties that return SimpleNamespace matching the structure
            # needed by the application logic. 
            # However, ConfigStore contract expects PipelineData (dataclass).
            
            # We need to construct the dataclass from the model.
            
            model_instance = await PipelineModel.objects.aget(name=name)
            return self._to_dataclass(model_instance)
            
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error retrieving pipeline {name}: {e}")
            return None

    async def list_pipelines(self) -> list[PipelineData]:
        """
        List all available pipelines.
        """
        pipelines = []
        try:
            # Async iteration over queryset
            async for model_instance in PipelineModel.objects.all():
                try:
                    pipelines.append(self._to_dataclass(model_instance))
                except Exception as e:
                    logger.error(f"Error converting pipeline {model_instance.name}: {e}")
        except Exception as e:
            logger.error(f"Error listing pipelines: {e}")
            
        return pipelines

    async def save_pipeline(self, pipeline: PipelineData) -> None:
        """
        Save a pipeline configuration.
        """
        defaults = {
            "description": pipeline.description,
            "enabled": pipeline.enabled,
            "query": pipeline.query,
            "step": pipeline.step,
            "context_window": pipeline.context_window,
            "prediction_horizon": pipeline.prediction_horizon,
            "mode": pipeline.mode,
            "forecast_schedule": pipeline.forecast_schedule,
            "anomaly_schedule": pipeline.anomaly_schedule,
            "series_type": pipeline.series_type,
            "covariates": pipeline.covariates,
            "model_config": pipeline.model.model_dump() if hasattr(pipeline.model, 'model_dump') else pipeline.model,
            "training_config": pipeline.training.model_dump() if hasattr(pipeline.training, 'model_dump') else pipeline.training,
            "anomaly_config": pipeline.anomaly.model_dump() if hasattr(pipeline.anomaly, 'model_dump') else pipeline.anomaly,
            "output_config": pipeline.output.model_dump() if hasattr(pipeline.output, 'model_dump') else pipeline.output,
        }
        
        await PipelineModel.objects.aupdate_or_create(name=pipeline.name, defaults=defaults)

    async def delete_pipeline(self, name: str) -> bool:
        """
        Delete a pipeline configuration.
        """
        try:
            p = await PipelineModel.objects.aget(name=name)
            await p.adelete()
            return True
        except ObjectDoesNotExist:
            return False

    def _to_dataclass(self, instance: PipelineModel) -> PipelineData:
        """
        Convert Django Model instance to Pipeline Dataclass.
        """
        # Using Pydantic adapter for robust validation/conversion 
        # based on the JSON fields stored in the model.
        # We reconstruct the dict first.
        
        data = {
            "name": instance.name,
            "description": instance.description or "",
            "enabled": instance.enabled,
            "query": instance.query,
            "step": instance.step,
            "context_window": instance.context_window,
            "prediction_horizon": instance.prediction_horizon,
            "mode": instance.mode,
            "forecast_schedule": instance.forecast_schedule,
            "anomaly_schedule": instance.anomaly_schedule,
            "series_type": instance.series_type,
            "covariates": instance.covariates,
            "model": instance.model_config,
            "training": instance.training_config,
            "anomaly": instance.anomaly_config,
            "output": instance.output_config,
            # Infrastructure overrides not currently in model but could be added?
            # Assuming None for now as they are runtime/env specific or need model update
            "prometheus_url": None, 
            "prometheus_write_url": None,
        }
        
        from pydantic import TypeAdapter
        adapter = TypeAdapter(PipelineData)
        return adapter.validate_python(data)
