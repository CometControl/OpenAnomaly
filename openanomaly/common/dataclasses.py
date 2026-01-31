"""
Result Domain Models - Data structures for forecast and anomaly results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Any


@dataclass
class ForecastPoint:
    """A single forecast point with optional uncertainty bounds."""
    
    timestamp: datetime
    value: float
    lower_bound: float | None = None
    upper_bound: float | None = None


@dataclass
class AnomalyScore:
    """Anomaly score for a single point."""
    
    timestamp: datetime
    actual_value: float
    predicted_value: float
    score: float  # 0.0 = normal, 1.0 = highly anomalous
    is_anomaly: bool = False


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    
    pipeline_name: str
    execution_time: datetime
    forecasts: list[ForecastPoint] = field(default_factory=list)
    anomaly_scores: list[AnomalyScore] = field(default_factory=list)
    error: str | None = None


@dataclass
class ForecastRequest:
    """Request for a forecast prediction."""
    
    prediction_length: int
    quantiles: list[float] = field(default_factory=lambda: [0.1, 0.5, 0.9])
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ForecastResult:
    """Result of a forecast prediction."""
    
    timestamps: list[datetime]
    mean: list[float]
    quantiles: dict[str, list[float]] | None = None


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""
    scores: list[float]
    anomalies: list[bool]


# --- Pipeline Configuration (Migrated from API Schemas) ---

@dataclass
class CovariateConfig:
    """Configuration for a covariate time series."""
    query: str
    name: str


@dataclass
class ModelConfig:
    """Configuration for the model engine."""
    type: Literal["local", "remote"]
    id: str | None = None  # HuggingFace model ID (for local)
    endpoint: str | None = None  # URL (for remote)
    serialization_format: Literal["json", "arrow"] = "json"
    parameters: dict = field(default_factory=dict)


@dataclass
class AnomalyConfig:
    """Configuration for anomaly detection."""
    technique: Literal["confidence_interval", "z_score", "iqr", "isolation_forest"] = "confidence_interval"
    confidence_level: float = 0.95
    threshold: float = 3.0


@dataclass
class OutputConfig:
    """Configuration for output metrics."""
    write_forecast: bool = True
    write_anomaly_score: bool = True
    metric_prefix: str = "openanomaly_"


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    enabled: bool = True
    schedule: str = "0 0 * * *"  # Daily at midnight
    window: str = "30d"  # Lookback window for training data
    endpoint: str | None = None
    parameters: dict = field(default_factory=dict)
    
    # Kafka configuration
    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "training-events"
    kafka_message_key: str = "{pipeline_name}"  # Template for message key
    kafka_message_template: dict = field(default_factory=dict)  # Custom message structure



@dataclass
class Pipeline:
    """
    Complete pipeline configuration.
    """
    # --- Identity ---
    name: str
    query: str  # Mandatory field moved up
    description: str = ""
    enabled: bool = True
    
    # --- Data Source ---
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
    covariates: list[CovariateConfig] = field(default_factory=list)
    
    # --- Model Configuration ---
    model: ModelConfig = field(default_factory=lambda: ModelConfig(type="local"))
    
    # --- Training Configuration ---
    training: TrainingConfig | None = None
    
    # --- Anomaly Detection ---
    anomaly: AnomalyConfig = field(default_factory=AnomalyConfig)
    
    # --- Output ---
    output: OutputConfig = field(default_factory=OutputConfig)
    
    # --- Infrastructure Overrides ---
    prometheus_url: str | None = None
    prometheus_write_url: str | None = None
