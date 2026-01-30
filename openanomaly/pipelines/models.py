
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Pipeline(models.Model):
    """
    Simplified Pipeline Model for Anomaly Detection.
    
    Each pipeline can run 3 independent scheduled tasks:
    1. Training - Periodically retrain models with historical data
    2. Forecast - Generate forecasts at regular intervals
    3. Anomaly Detection - Detect anomalies in real-time data
    
    All tasks share the same query and metadata.
    """
    if settings.DB_TYPE == 'mongodb':
        from django_mongodb_backend.fields import ObjectIdAutoField
        id = ObjectIdAutoField(primary_key=True)

    # ===== Core Metadata =====
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique name for this pipeline"
    )
    description = models.TextField(
        blank=True,
        help_text="What does this pipeline do?"
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Master switch - disable to stop all tasks"
    )
    
    # ===== Data Source =====
    query = models.TextField(
        help_text="PromQL query to fetch time series data"
    )
    step = models.CharField(
        max_length=50,
        default="1m",
        help_text="Query step size (e.g., '1m', '30s')"
    )
    
    # ===== Task 1: Training =====
    training_enabled = models.BooleanField(
        default=False,
        help_text="Enable periodic model training"
    )
    training_schedule = models.CharField(
        max_length=100,
        default="0 */6 * * *",
        help_text="Cron expression for training (default: every 6 hours)"
    )
    training_window = models.CharField(
        max_length=50,
        default="7d",
        help_text="How much historical data to use for training (e.g., '7d', '30d')"
    )
    
    # ===== Task 2: Forecast =====
    forecast_enabled = models.BooleanField(
        default=True,
        help_text="Enable forecast generation"
    )
    forecast_schedule = models.CharField(
        max_length=100,
        default="*/5 * * * *",
        help_text="Cron expression for forecasting (default: every 5 minutes)"
    )
    forecast_context_window = models.CharField(
        max_length=50,
        default="1h",
        help_text="Historical context for forecasting (e.g., '1h', '2h')"
    )
    forecast_horizon = models.CharField(
        max_length=50,
        default="15m",
        help_text="How far ahead to forecast (e.g., '15m', '1h')"
    )
    
    # ===== Task 3: Anomaly Detection =====
    anomaly_enabled = models.BooleanField(
        default=True,
        help_text="Enable anomaly detection"
    )
    anomaly_schedule = models.CharField(
        max_length=100,
        default="*/1 * * * *",
        help_text="Cron expression for anomaly detection (default: every minute)"
    )
    anomaly_threshold = models.FloatField(
        default=3.0,
        help_text="Anomaly sensitivity (higher = less sensitive, e.g., 3.0 for 3-sigma)"
    )
    
    # ===== Metadata =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Pipeline'
        verbose_name_plural = 'Pipelines'
    
    def __str__(self):
        return self.name
    
    # ===== Helper Properties for Task Status =====
    @property
    def active_tasks(self):
        """Returns list of enabled task names."""
        tasks = []
        if self.training_enabled:
            tasks.append('Training')
        if self.forecast_enabled:
            tasks.append('Forecast')
        if self.anomaly_enabled:
            tasks.append('Anomaly')
        return tasks
    
    @property
    def is_fully_active(self):
        """True if pipeline is enabled and at least one task is enabled."""
        return self.enabled and len(self.active_tasks) > 0
