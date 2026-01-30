
from openanomaly.common.interfaces.scheduler import Scheduler
# from openanomaly.core.domain.pipeline import Pipeline # Removed
from typing import Callable, List
from asgiref.sync import sync_to_async
from django.conf import settings
import logging

# We need to setup Django to use models outside of a request context
# But since this code runs inside the main app (FastAPI) which might initialize Django,
# we should ensure it's safe. Use sync_to_async for DB operations.

# Import JobModel lazily or within methods to avoid AppRegistryNotReady if imported at module level before setup
# However, typical pattern is to import inside the method.

logger = logging.getLogger(__name__)

class DjangoSchedulerAdapter(Scheduler):
    """
    Scheduler implementation using Django ORM and Redbeat (via Signals).
    """

    async def schedule_pipeline(self, pipeline, task: Callable) -> str:
        # logic is now handled by Pipeline.save() triggering signals.
        # This method effectively ensures the Pipeline exists in Django DB.
        # "pipeline" arg here is likely the Pydantic model from the Core service.
        # BUT we are refactoring to Django-Native.
        # If the Core Service is passing a Pydantic model, we need to map it to Django.
        
        from openanomaly.adapters.django_app.pipelines.models import Pipeline as DjangoPipeline
        
        # Mapping (Simple serialization/deserialization or field copy)
        # Assuming 'pipeline' is a Pydantic object
        defaults = {
            "query": pipeline.query,
            "step": pipeline.step,
            "context_window": pipeline.context_window,
            "prediction_horizon": pipeline.prediction_horizon,
            "mode": pipeline.mode,
            "forecast_schedule": pipeline.forecast_schedule,
            "anomaly_schedule": pipeline.anomaly_schedule,
            "series_type": pipeline.series_type,
            "model_config": pipeline.model.model_dump() if hasattr(pipeline.model, 'model_dump') else pipeline.model.dict(),
            "anomaly_config": pipeline.anomaly.model_dump() if hasattr(pipeline.anomaly, 'model_dump') else pipeline.anomaly.dict(),
            "enabled": True
        }
        
        await sync_to_async(self._update_or_create_pipeline)(pipeline.name, defaults)
        return f"pipeline_{pipeline.name}_forecast"

    def _update_or_create_pipeline(self, name, defaults):
        from openanomaly.adapters.django_app.pipelines.models import Pipeline as DjangoPipeline
        DjangoPipeline.objects.update_or_create(name=name, defaults=defaults)

    async def unschedule_pipeline(self, pipeline_name: str) -> bool:
        return await sync_to_async(self._disable_pipeline)(pipeline_name)

    def _disable_pipeline(self, name):
        from openanomaly.adapters.django_app.pipelines.models import Pipeline as DjangoPipeline
        try:
            p = DjangoPipeline.objects.get(name=name)
            p.enabled = False
            p.save()
            return True
        except DjangoPipeline.DoesNotExist:
            return False

    async def list_scheduled(self) -> List[str]:
        from openanomaly.adapters.django_app.pipelines.models import Pipeline as DjangoPipeline
        return await sync_to_async(list)(
            DjangoPipeline.objects.filter(enabled=True).values_list('name', flat=True)
        )
