"""
ModelEngine Port - Interface for Time Series Foundation Model inference.
"""

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    """Request for a forecast prediction."""
    
    # We pass the dataframe directly in Python, but for Remote Adapter serialization
    # we might need to serialize it. The interface accepts DataFrame.
    # But Pydantic models are good for the Remote API contract.
    
    prediction_length: int
    quantiles: list[float] = Field(default_factory=lambda: [0.1, 0.5, 0.9])
    parameters: dict[str, Any] = Field(default_factory=dict)


class ForecastResult(BaseModel):
    """Result of a forecast prediction."""
    
    # Returns a DataFrame in the 'forecast' field usually, but for strict typing:
    timestamps: list[datetime]
    mean: list[float]
    quantiles: dict[str, list[float]] | None = None  # e.g. "0.9": [...]


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
    async def health_check(self) -> bool:
        """Check if model engine is healthy."""
        ...
