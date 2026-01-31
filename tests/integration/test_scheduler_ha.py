import pytest
import time
import redis
import os
from redbeat import RedBeatSchedulerEntry
from celery.schedules import schedule


def test_scheduler_ha_deduplication():
    """
    Test that multiple beat instances don't duplicate tasks.
    We use RedBeat to dynamically add a task.
    """
    import django
    from django.conf import settings
    # Ensure Django is setup
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'openanomaly.config.settings')
        django.setup()
        
    from openanomaly.config.celery import app as celery_app

    redis_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
    r = redis.from_url(redis_url)
    
    # Clean up previous runs
    r.delete("scheduler:heartbeat:count")
    
    # Define a dynamic task running every 1 second
    entry_name = 'test-heartbeat'
    interval = 1.0 # seconds
    
    # Delete if exists (RedBeat stores schedule in Redis)
    try:
        e = RedBeatSchedulerEntry.from_key(f"redbeat:{entry_name}", app=celery_app)
        e.delete()
    except KeyError:
        pass
        
    # Create new schedule entry
    entry = RedBeatSchedulerEntry(
        entry_name,
        'openanomaly.tasks.heartbeat',
        schedule(run_every=interval),
        args=[time.time()],
        app=celery_app
    )
    entry.save()
    print(f"\nScheduled '{entry_name}' every {interval}s.")
    print(f"Entry Key: {entry.key}")
    
    # Debug: List all redbeat keys
    keys = r.keys("redbeat*")
    print(f"Current RedBeat Keys: {keys}")
    
    # Wait and measure
    duration = 10
    print(f"Waiting {duration}s for heartbeats...")
    time.sleep(duration)
    
    # Check count
    count_bytes = r.get("scheduler:heartbeat:count")
    count = int(count_bytes) if count_bytes else 0
    
    print(f"\nActual Heartbeats: {count}")
    print(f"Expected Heartbeats: ~{duration}")
    
    # Cleanup
    entry.delete()
    r.delete("scheduler:heartbeat:count")
    
    # Assertions
    # We expect roughly 1 per second. 
    # If 2 beats were running without locking, we'd see ~20.
    # Allow some buffer for startup/jitter.
    assert 8 <= count <= 12, f"Expected ~10 executions, got {count}. Duplication occurred!"

if __name__ == "__main__":
    test_scheduler_ha_deduplication()
