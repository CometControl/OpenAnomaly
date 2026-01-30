
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Pipeline
from redbeat import RedBeatSchedulerEntry
from celery.schedules import crontab
from celery import current_app
import logging

logger = logging.getLogger(__name__)

def parse_cron(expression):
    """
    Parses a cron expression into a celery.schedules.crontab object.
    Assumes standard 5-part cron: minute hour day_of_month month_of_year day_of_week
    """
    try:
        parts = expression.split()
        if len(parts) != 5:
            # Fallback or error
            return None
        return crontab(
            minute=parts[0],
            hour=parts[1],
            day_of_month=parts[2],
            month_of_year=parts[3],
            day_of_week=parts[4]
        )
    except Exception:
        return None

@receiver(post_save, sender=Pipeline)
def sync_pipeline_to_redbeat(sender, instance, **kwargs):
    """
    Sync Pipeline schedules to Redbeat.
    Creates/updates/deletes RedBeat schedule entries based on task enable flags.
    """
    
    # 1. Forecast Schedule
    forecast_key = f"redbeat:pipeline_{instance.name}_forecast"
    if instance.enabled and instance.forecast_enabled:
        schedule_obj = parse_cron(instance.forecast_schedule)
        if schedule_obj:
            entry = RedBeatSchedulerEntry(
                name=f"pipeline_{instance.name}_forecast",
                task="openanomaly.tasks.run_forecast",
                schedule=schedule_obj,
                args=[instance.name],
                app=current_app
            )
            try:
                entry.save()
                logger.info(f"Synced forecast job for {instance.name}")
            except Exception as e:
                logger.warning(f"Failed to sync forecast job for {instance.name} to RedBeat: {e}")
    else:
        try:
            RedBeatSchedulerEntry.from_key(forecast_key, app=current_app).delete()
        except KeyError:
            pass
        except Exception as e:
            logger.warning(f"Failed to remove forecast job key: {e}")

    # 2. Anomaly Schedule
    anomaly_key = f"redbeat:pipeline_{instance.name}_anomaly"
    if instance.enabled and instance.anomaly_enabled:
        schedule_obj = parse_cron(instance.anomaly_schedule)
        if schedule_obj:
            entry = RedBeatSchedulerEntry(
                name=f"pipeline_{instance.name}_anomaly",
                task="openanomaly.tasks.run_anomaly_check",
                schedule=schedule_obj,
                args=[instance.name],
                app=current_app
            )
            try:
                entry.save()
                logger.info(f"Synced anomaly job for {instance.name}")
            except Exception as e:
                logger.warning(f"Failed to sync anomaly job for {instance.name} to RedBeat: {e}")
    else:
        try:
            RedBeatSchedulerEntry.from_key(anomaly_key, app=current_app).delete()
        except KeyError:
            pass
        except Exception as e:
            logger.warning(f"Failed to remove anomaly job key: {e}")

    # 3. Training Schedule
    training_key = f"redbeat:pipeline_{instance.name}_training"
    if instance.enabled and instance.training_enabled:
        schedule_obj = parse_cron(instance.training_schedule)
        if schedule_obj:
            entry = RedBeatSchedulerEntry(
                name=f"pipeline_{instance.name}_training",
                task="openanomaly.tasks.train_model",
                schedule=schedule_obj,
                args=[instance.name],
                app=current_app
            )
            try:
                entry.save()
                logger.info(f"Synced training job for {instance.name}")
            except Exception as e:
                logger.warning(f"Failed to sync training job for {instance.name} to RedBeat: {e}")
    else:
        try:
            RedBeatSchedulerEntry.from_key(training_key, app=current_app).delete()
        except KeyError:
            pass
        except Exception as e:
            logger.warning(f"Failed to remove training job key: {e}")

@receiver(post_delete, sender=Pipeline)
def delete_pipeline_from_redbeat(sender, instance, **kwargs):
    """
    Remove all RedBeat schedule entries when a pipeline is deleted.
    """
    keys = [
        f"redbeat:pipeline_{instance.name}_forecast",
        f"redbeat:pipeline_{instance.name}_anomaly",
        f"redbeat:pipeline_{instance.name}_training"
    ]
    for key in keys:
        try:
            RedBeatSchedulerEntry.from_key(key, app=current_app).delete()
        except Exception:
            pass
