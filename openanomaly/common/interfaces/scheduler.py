"""
Scheduler Port - Interface for scheduling and triggering inference jobs.

This port defines the contract for job scheduling.
The primary implementation uses Celery Beat.
"""

from abc import ABC, abstractmethod
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from openanomaly.pipelines.models import Pipeline as DjangoPipeline
    from openanomaly.common.dataclasses import Pipeline as PipelineSchema
    Pipeline = DjangoPipeline | PipelineSchema


class Scheduler(ABC):
    """
    Abstract interface for job scheduling.
    
    Primary implementation: CeleryBeatAdapter
    """
    
    @abstractmethod
    async def schedule_pipeline(
        self,
        pipeline: "Pipeline",
        task: Callable,
    ) -> str:
        """
        Schedule a pipeline's inference job.
        
        Args:
            pipeline: Pipeline with schedule configuration
            task: The Celery task to execute
            
        Returns:
            Schedule ID for reference
        """
        ...
    
    @abstractmethod
    async def unschedule_pipeline(self, pipeline_name: str) -> bool:
        """
        Remove a pipeline from the schedule.
        
        Args:
            pipeline_name: Name of the pipeline to unschedule
            
        Returns:
            True if removed, False if not found
        """
        ...
    
    @abstractmethod
    async def list_scheduled(self) -> list[str]:
        """
        List all currently scheduled pipeline names.
        
        Returns:
            List of pipeline names
        """
        ...
