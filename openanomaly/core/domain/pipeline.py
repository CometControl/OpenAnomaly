"""
Pipeline Domain Model - Core data structures for pipeline configuration.

Uses Pydantic for validation and schema generation.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CovariateConfig(BaseModel):
    """Configuration for a covariate time series."""
    
    query: str
    name: str


class ModelConfig(BaseModel):
    """Configuration for the model engine."""
    
    type: Literal["local", "remote"]
    id: str | None = None  # HuggingFace model ID (for local)
    endpoint: str | None = None  # URL (for remote)
    serialization_format: Literal["json", "parquet"] = "json"  # Data format for remote calls
    parameters: dict = Field(default_factory=dict)


class AnomalyConfig(BaseModel):
    """Configuration for anomaly detection."""
    
    technique: Literal["confidence_interval", "z_score", "iqr", "isolation_forest"] = "confidence_interval"
    confidence_level: float = 0.95
    threshold: float = 3.0


class OutputConfig(BaseModel):
    """Configuration for output metrics."""
    
    write_forecast: bool = True
    write_anomaly_score: bool = True
    metric_prefix: str = "openanomaly_"


class TrainingConfig(BaseModel):
    """Configuration for model training."""
    
    enabled: bool = True
    schedule: str = "0 0 * * *"  # Daily at midnight
    window: str = "30d"  # Lookback window for training data
    endpoint: str | None = None  # Full URL for training (e.g. http://host/fit)
    parameters: dict = Field(default_factory=dict)  # Training-specific parameters


class Pipeline(BaseModel):
    """
    Complete pipeline configuration.
    
    Matches the JSON Schema defined in technical_design.md Section 5.
    """
    
    # --- Identity ---
    name: str
    description: str = ""
    enabled: bool = True
    
    # --- Data Source ---
    query: str
    step: str = "1m"
    
    # --- Time Windows ---
    context_window: str = "1h"
    prediction_horizon: str = "15m"
    
    # --- Mode ---
    mode: Literal["forecast_only", "anomaly_only", "forecast_and_anomaly"] = "forecast_and_anomaly"
    
    # --- Scheduling ---
    forecast_schedule: str = "*/5 * * * *"
    anomaly_schedule: str = "*/1 * * * *"
    
    # --- Series Type ---
    series_type: Literal["univariate", "multivariate", "covariate"] = "univariate"
    covariates: list[CovariateConfig] = Field(default_factory=list)
    
    # --- Model Configuration ---
    model: ModelConfig = Field(default_factory=lambda: ModelConfig(type="local"))
    
    # --- Training Configuration ---
    training: TrainingConfig | None = Field(default=None)
    
    # --- Anomaly Detection ---
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)
    
    # --- Output ---
    output: OutputConfig = Field(default_factory=OutputConfig)
