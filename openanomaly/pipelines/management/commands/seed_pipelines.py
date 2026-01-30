"""
Management command to seed the database with sample pipelines.
"""
from django.core.management.base import BaseCommand
from openanomaly.pipelines.models import Pipeline


class Command(BaseCommand):
    help = 'Seeds the database with sample pipelines for demo/development'

    def handle(self, *args, **options):
        self.stdout.write('Seeding sample pipelines...')
        
        # Sample pipeline configurations
        sample_pipelines = [
            {
                "name": "prometheus_up_monitoring",
                "description": "Monitor Prometheus availability with forecasts and anomaly detection",
                "enabled": True,
                "query": "up{job=\"prometheus\"}",
                "step": "1m",
                # Training
                "training_enabled": True,
                "training_schedule": "0 */12 * * *",  # Every 12 hours
                "training_window": "7d",
                # Forecast
                "forecast_enabled": True,
                "forecast_schedule": "*/5 * * * *",  # Every 5 minutes
                "forecast_context_window": "1h",
                "forecast_horizon": "15m",
                # Anomaly
                "anomaly_enabled": True,
                "anomaly_schedule": "*/1 * * * *",  # Every minute
                "anomaly_threshold": 3.0,
            },
            {
                "name": "cpu_usage_forecast",
                "description": "Forecast CPU usage trends (forecast only)",
                "enabled": True,
                "query": "rate(process_cpu_seconds_total[5m])",
                "step": "30s",
                # Training
                "training_enabled": False,
                "training_schedule": "0 */6 * * *",
                "training_window": "14d",
                # Forecast
                "forecast_enabled": True,
                "forecast_schedule": "*/10 * * * *",  # Every 10 minutes
                "forecast_context_window": "2h",
                "forecast_horizon": "30m",
                # Anomaly
                "anomaly_enabled": False,
                "anomaly_schedule": "*/5 * * * *",
                "anomaly_threshold": 2.5,
            },
            {
                "name": "memory_anomaly_detection",
                "description": "Detect memory usage anomalies (anomaly only)",
                "enabled": True,
                "query": "process_resident_memory_bytes",
                "step": "1m",
                # Training
                "training_enabled": True,
                "training_schedule": "0 */8 * * *",  # Every 8 hours
                "training_window": "7d",
                # Forecast
                "forecast_enabled": False,
                "forecast_schedule": "*/15 * * * *",
                "forecast_context_window": "4h",
                "forecast_horizon": "1h",
                # Anomaly
                "anomaly_enabled": True,
                "anomaly_schedule": "*/2 * * * *",  # Every 2 minutes
                "anomaly_threshold": 2.5,
            }
        ]
        
        created_count = 0
        skipped_count = 0
        
        for pipeline_data in sample_pipelines:
            pipeline_name = pipeline_data["name"]
            
            # Check if pipeline already exists
            if Pipeline.objects.filter(name=pipeline_name).exists():
                self.stdout.write(
                    self.style.WARNING(f'  Pipeline "{pipeline_name}" already exists, skipping')
                )
                skipped_count += 1
                continue
            
            # Create the pipeline
            Pipeline.objects.create(**pipeline_data)
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Created pipeline: {pipeline_name}')
            )
            created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSeeding complete! Created {created_count}, skipped {skipped_count} existing pipelines.'
            )
        )
