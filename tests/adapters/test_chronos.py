"""
Tests for ChronosAdapter.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from openanomaly.common.adapters.models.chronos.adapter import ChronosAdapter
from openanomaly.common.dataclasses import ForecastRequest

@pytest.fixture
def mock_pipeline():
    """Mock the Chronos2Pipeline."""
    with patch("openanomaly.common.adapters.models.chronos.adapter.Chronos2Pipeline") as MockPipeline:
        # Setup the mock instance
        pipeline_instance = MockPipeline.from_pretrained.return_value
        
        # Mock predict_df to return a valid DataFrame
        # Chronos returns: unique_id, ds, "0.1", "0.5", "0.9", "mean"
        def side_effect_predict(df, **kwargs):
            future_dates = pd.date_range(start=df['ds'].iloc[-1], periods=kwargs['prediction_length'] + 1, freq='1min')[1:]
            return pd.DataFrame({
                "unique_id": ["test_id"] * len(future_dates),
                "ds": future_dates,
                "0.1": np.random.rand(len(future_dates)),
                "0.5": np.random.rand(len(future_dates)),
                "0.9": np.random.rand(len(future_dates)),
                "mean": np.random.rand(len(future_dates)),
            })
            
        pipeline_instance.predict_df.side_effect = side_effect_predict
        yield pipeline_instance

@pytest.mark.asyncio
async def test_chronos_predict_flow(mock_pipeline):
    """Test full prediction flow with mocked pipeline."""
    adapter = ChronosAdapter(model_id="amazon/chronos-t5-tiny")
    
    # Input DataFrame (Standard Nixtla format)
    input_df = pd.DataFrame({
        "unique_id": ["test_id"] * 10,
        "ds": pd.date_range(start="2024-01-01", periods=10, freq="1min"),
        "y": np.random.rand(10)
    })
    
    request = ForecastRequest(
        prediction_length=5,
        quantiles=[0.1, 0.5, 0.9]
    )
    
    # Execute
    result = await adapter.predict(input_df, request)
    
    # Assertions
    assert "q_0.1" in result.columns, "Output should map '0.1' to 'q_0.1'"
    assert "q_0.9" in result.columns
    assert len(result) == 5
    
    # Verify predict_df arguments
    mock_pipeline.predict_df.assert_called_once()
    call_kwargs = mock_pipeline.predict_df.call_args.kwargs
    assert call_kwargs["prediction_length"] == 5
    assert call_kwargs["target"] == "y"
    assert call_kwargs["id_column"] == "unique_id"

@pytest.mark.asyncio
async def test_chronos_missing_columns():
    """Test validation failure."""
    adapter = ChronosAdapter(model_id="test")
    # Missing 'y'
    bad_df = pd.DataFrame({
        "unique_id": ["id"],
        "ds": [pd.Timestamp("2024-01-01")]
    })
    
    with pytest.raises(ValueError, match="must contain columns"):
        await adapter.predict(bad_df, ForecastRequest(prediction_length=1))
