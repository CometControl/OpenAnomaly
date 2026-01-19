"""
Tests for Core Domain Models (Pipeline).
"""
import pytest
from openanomaly.core.domain.pipeline import Pipeline, ModelConfig, OutputConfig

def test_pipeline_defaults():
    """Test standard pipeline defaults."""
    pipeline = Pipeline(
        name="test-pipeline",
        query="up",
    )
    assert pipeline.step == "1m"
    assert pipeline.model.type == "local"
    assert pipeline.enabled is True
    assert pipeline.anomaly.technique == "confidence_interval"
    assert pipeline.series_type == "univariate"

def test_pipeline_validation():
    """Test validation logic."""
    # Example: Invalid schedule cron (Pydantic might not validate cron syntax by default without extra validator, 
    # but let's check basic type/presence)
    with pytest.raises(Exception):
        # Missing required 'query'
        Pipeline(name="broken")

def test_pipeline_model_config():
    """Test nested model configuration."""
    pipeline = Pipeline(
        name="chronos-pipe",
        query="metric",
        model=ModelConfig(
            type="remote",
            parameters={"model_id": "amazon/chronos-t5-tiny"}
        )
    )
    assert pipeline.model.type == "remote"
    assert pipeline.model.parameters["model_id"] == "amazon/chronos-t5-tiny"
