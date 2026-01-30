from django.contrib import admin
from .models import Pipeline


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    """
    Admin interface for Pipeline model with organized fieldsets.
    """
    
    # List view configuration
    list_display = ['name', 'enabled', 'training_status', 'forecast_status', 'anomaly_status', 'created_at']
    list_filter = ['enabled', 'training_enabled', 'forecast_enabled', 'anomaly_enabled']
    search_fields = ['name', 'description', 'query']
    ordering = ['-created_at']
    
    # Form configuration with organized fieldsets
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'enabled'),
            'description': 'Core pipeline settings'
        }),
        ('Data Source', {
            'fields': ('query', 'step'),
            'description': 'PromQL query configuration'
        }),
        ('Training Schedule', {
            'fields': ('training_enabled', 'training_schedule', 'training_window'),
            'description': 'Periodic model training settings',
            'classes': ('collapse',)
        }),
        ('Forecast Schedule', {
            'fields': ('forecast_enabled', 'forecast_schedule', 'forecast_context_window', 'forecast_horizon'),
            'description': 'Forecast generation settings',
            'classes': ('collapse',)
        }),
        ('Anomaly Detection Schedule', {
            'fields': ('anomaly_enabled', 'anomaly_schedule', 'anomaly_threshold'),
            'description': 'Anomaly detection settings',
            'classes': ('collapse',)
        }),
    )
    
    # Custom methods for list display
    def training_status(self, obj):
        return '✓ Enabled' if obj.training_enabled else '✗ Disabled'
    training_status.short_description = 'Training'
    
    def forecast_status(self, obj):
        return '✓ Enabled' if obj.forecast_enabled else '✗ Disabled'
    forecast_status.short_description = 'Forecast'
    
    def anomaly_status(self, obj):
        return '✓ Enabled' if obj.anomaly_enabled else '✗ Disabled'
    anomaly_status.short_description = 'Anomaly'
