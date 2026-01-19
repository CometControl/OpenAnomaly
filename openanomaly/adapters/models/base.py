"""
Base Model Engine - Abstract base class for all model adapters.
"""

from openanomaly.core.ports.model_engine import ModelEngine


class BaseModelAdapter(ModelEngine):
    """
    Base class for model adapters.
    
    Provides common functionality for both local and remote adapters.
    """
    
    def __init__(self, config: dict | None = None):
        self.config = config or {}
