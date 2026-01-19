"""
Result Domain Models - Data structures for forecast and anomaly results.
"""

from dataclasses import dataclass, field
from datetime import datetime


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
