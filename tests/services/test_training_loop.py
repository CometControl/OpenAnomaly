"""
Tests for TrainingLoop service.
"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock
from datetime import timedelta

from openanomaly.pipelines.training import TrainingLoop
from openanomaly.pipelines.models import Pipeline

@pytest.fixture
def mock_tsdb():
    tsdb = MagicMock()
    # Return some dummy data
    tsdb.read_series.return_value = pd.DataFrame({
        "ds": pd.date_range("2024-01-01", periods=10, freq="D"),
        "y": range(10),
        "unique_id": "test_id"
    })
    return tsdb

@pytest.fixture
def mock_model():
    model = MagicMock()
    model.train = AsyncMock(return_value="new_model_id_123")
    return model

@pytest.mark.asyncio
async def test_training_loop_success(mock_tsdb, mock_model):
    """Test successful training flow."""
    pipeline = Pipeline(
        name="test_pipeline",
        query="up",
        training=TrainingConfig(
            enabled=True,
            window="30d",
            parameters={"epochs": 10}
        )
    )
    
    service = TrainingLoop(mock_tsdb, mock_model)
    result = await service.run_training(pipeline)
    
    assert result == "new_model_id_123"
    
    # Verify TSDB read
    mock_tsdb.read_series.assert_called_once()
    _, kwargs = mock_tsdb.read_series.call_args
    assert "start" in kwargs and "end" in kwargs
    
    # Verify Model train
    mock_model.train.assert_called_once()
    args, kwargs = mock_model.train.call_args
    assert len(kwargs['df']) == 10  # 10 rows from mock_tsdb
    assert kwargs["parameters"] == {"epochs": 10}

@pytest.mark.asyncio
async def test_training_disabled(mock_tsdb, mock_model):
    """Test when training is disabled."""
    pipeline = Pipeline(
        name="test_pipeline",
        query="up",
        training=TrainingConfig(enabled=False)
    )
    
    service = TrainingLoop(mock_tsdb, mock_model)
    result = await service.run_training(pipeline)
    
    assert result is None
    mock_tsdb.read_series.assert_not_called()
    mock_model.train.assert_not_called()

@pytest.mark.asyncio
async def test_training_no_config(mock_tsdb, mock_model):
    """Test when training config is None."""
    pipeline = Pipeline(
        name="test_pipeline",
        query="up",
        training=None
    )
    
    service = TrainingLoop(mock_tsdb, mock_model)
    result = await service.run_training(pipeline)
    
    assert result is None
    mock_model.train.assert_not_called()
