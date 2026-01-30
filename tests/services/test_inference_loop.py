"""
Tests for InferenceLoop Service.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, AsyncMock

from openanomaly.pipelines.inference import InferenceLoop
from openanomaly.common.interfaces.tsdb_client import TSDBClient
from openanomaly.common.interfaces.model_engine import ModelEngine
from openanomaly.pipelines.models import Pipeline

@pytest.fixture
def mock_tsdb():
    tsdb = MagicMock(spec=TSDBClient)
    tsdb.query_range = AsyncMock()
    tsdb.write = AsyncMock()
    return tsdb

@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=ModelEngine)
    engine.predict = AsyncMock()
    return engine

@pytest.fixture
def sample_pipeline():
    return Pipeline(
        name="test-pipe",
        query="up",
        model=ModelConfig(type="local"),
        output={"write_forecast": True}
    )

@pytest.mark.asyncio
async def test_run_pipeline_success(mock_tsdb, mock_engine, sample_pipeline):
    """Test successful run cycle."""
    service = InferenceLoop(mock_tsdb, mock_engine)
    
    # Mock data return
    mock_tsdb.query_range.return_value = pd.DataFrame({
        "ds": pd.date_range("2024-01-01", periods=10, freq="1m"),
        "y": np.random.rand(10),
        "unique_id": "up"
    })
    
    # Mock prediction return
    mock_engine.predict.return_value = pd.DataFrame({
        "ds": pd.date_range("2024-01-01 10:10", periods=5, freq="1m"),
        "y": np.random.rand(5),
        "unique_id": "up",
        "mean": np.random.rand(5),
        "q_0.9": np.random.rand(5)
    })
    
    # Execute
    await service.run_pipeline(sample_pipeline)
    
    # Verify interactions
    mock_tsdb.query_range.assert_awaited_once()
    mock_engine.predict.assert_awaited_once()
    mock_tsdb.write.assert_awaited_once()

@pytest.mark.asyncio
async def test_run_cycle_empty_data(mock_tsdb, mock_engine, sample_pipeline):
    """Test handling of empty source data."""
    service = InferenceLoop(mock_tsdb, mock_engine)
    
    mock_tsdb.query_range.return_value = pd.DataFrame() # Empty
    
    await service.run_pipeline(sample_pipeline)
    
    # Should skip prediction and write
    mock_engine.predict.assert_not_awaited()
    mock_tsdb.write.assert_not_awaited()
