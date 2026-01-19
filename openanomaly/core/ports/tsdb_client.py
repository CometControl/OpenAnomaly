"""
TSDBClient Port - Interface for Time Series Database operations.
Returns Pandas DataFrames for easy integration with ML libraries.
"""

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class TSDBClient(ABC):
    """
    Abstract interface for Time Series Database operations.
    """
    
    @abstractmethod
    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str,
    ) -> pd.DataFrame:
        """
        Execute a range query against the TSDB.
        
        Args:
            query: PromQL query string
            start: Start time
            end: End time
            step: Resolution
            
        Returns:
            DataFrame with columns: ['ds', 'y', 'unique_id'] (Nixtla/Chronos compatible)
            - ds: timestamp
            - y: value
            - unique_id: metric identifier
        """
        ...
    
    @abstractmethod
    async def write(
        self,
        df: pd.DataFrame,
    ) -> None:
        """
        Write time series data to the TSDB.
        
        Args:
            df: DataFrame with columns ['ds', 'y', 'unique_id'] and optional label cols
        """
        ...
