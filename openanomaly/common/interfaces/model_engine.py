"""
ModelEngine Port - Interface for Time Series Foundation Model inference.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


from openanomaly.common.dataclasses import ForecastRequest, ForecastResult


class ModelEngine(ABC):
    """
    Abstract interface for Time Series Foundation Model inference.
    """
    
    @abstractmethod
    async def predict(
        self,
        df: pd.DataFrame,
        request: ForecastRequest
    ) -> pd.DataFrame:
        """
        Generate a forecast prediction.
        
        Args:
            df: Input DataFrame ['ds', 'y', 'unique_id']
            request: Configuration parameters
            
        Returns:
            DataFrame with forecast columns ['ds', 'unique_id', 'mean', 'q_0.1', ...]
        """
        ...
    
    @abstractmethod
    async def train(
        self,
        df: pd.DataFrame,
        parameters: dict[str, Any]
    ) -> str:
        """
        Train the model.
        
        Args:
            df: Input DataFrame ['ds', 'y', 'unique_id']
            parameters: Training hyperparameters
            
        Returns:
            str: Model ID or Artifact URI of the trained model
        """
        ...
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if model engine is healthy."""
        ...
