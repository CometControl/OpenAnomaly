"""
ConfigStore Port - Interface for loading and persisting pipeline configurations.

This port defines the contract for reading and writing pipeline definitions.
Implementations can be file-based (YAML) or database-backed (MongoDB).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openanomaly.core.domain.pipeline import Pipeline


class ConfigStore(ABC):
    """
    Abstract interface for pipeline configuration storage.
    
    Implementations:
    - YamlAdapter: File-based configuration
    - MongoAdapter: Database-backed configuration
    """
    
    @abstractmethod
    async def list_pipelines(self) -> list["Pipeline"]:
        """
        List all configured pipelines.
        
        Returns:
            List of Pipeline objects
        """
        ...
    
    @abstractmethod
    async def get_pipeline(self, name: str) -> "Pipeline | None":
        """
        Get a specific pipeline by name.
        
        Args:
            name: Pipeline name
            
        Returns:
            Pipeline if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def save_pipeline(self, pipeline: "Pipeline") -> None:
        """
        Save or update a pipeline.
        
        Args:
            pipeline: Pipeline to save
        """
        ...
    
    @abstractmethod
    async def delete_pipeline(self, name: str) -> bool:
        """
        Delete a pipeline by name.
        
        Args:
            name: Pipeline name
            
        Returns:
            True if deleted, False if not found
        """
        ...
