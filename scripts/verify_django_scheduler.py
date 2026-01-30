
import os
import sys
import django
from unittest.mock import MagicMock

# Setup Django Path
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openanomaly.config.settings")

def verify():
    print("Initializing Django...")
    django.setup()
    print("Django initialized successfully.")

    from openanomaly.pipelines.models import Pipeline
    import openanomaly.pipelines.signals as signals
    
    # Mock RedBeatSchedulerEntry to avoid Redis connection error if Redis is not running
    # but we want to verify the signal logic executes.
    original_entry_class = signals.RedBeatSchedulerEntry
    mock_entry = MagicMock()
    signals.RedBeatSchedulerEntry = mock_entry
    
    print("Creating test pipeline...")
    pipeline_name = "test_verification_pipeline"
    
    # Cleanup previous run
    Pipeline.objects.filter(name=pipeline_name).delete()
    
    # Create Pipeline
    pipeline = Pipeline.objects.create(
        name=pipeline_name,
        query="up",
        forecast_schedule="*/5 * * * *",
        mode=Pipeline.Mode.FORECAST_ONLY,
        model_config={"type": "local", "id": "test-model"}
    )
    print(f"Pipeline created: {pipeline}")
    
    # Check if signal called RedBeatSchedulerEntry constructor and save()
    if mock_entry.call_count > 0:
        print("SUCCESS: RedbetaSchedulerEntry was instantiated via signal.")
        # Verify call args
        call_args = mock_entry.call_args
        print(f"Call args: {call_args}")
    else:
        print("FAILURE: RedBeatSchedulerEntry was NOT instantiated.")
    
    # Check DB
    exists = Pipeline.objects.filter(name=pipeline_name).exists()
    if exists:
         print("SUCCESS: Pipeline exists in MongoDB (via Django ORM).")
    else:
         print("FAILURE: Pipeline not found in DB.")
         
    # Clean up
    pipeline.delete()
    print("Pipeline deleted.")
    
    print("Verification complete.")

if __name__ == "__main__":
    try:
        verify()
    except Exception as e:
        print(f"Verification FAILED with error: {e}")
        import traceback
        traceback.print_exc()
