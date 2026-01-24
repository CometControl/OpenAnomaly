import pytest
import os
from openanomaly.core.domain.settings import SystemSettings
from openanomaly.core.domain.pipeline import Pipeline
from openanomaly.adapters.config.mongo_store import MongoConfigStore

# Integration tests usually require custom markers or env vars to run
# We check if we can connect; if not, we skip.

@pytest.fixture
async def real_mongo_store():
    # Use default localhost:27017 or env var
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = "test_openanomaly_integration"
    
    settings = SystemSettings(
        config_store_type="mongo",
        mongo_url=mongo_url,
        mongo_db_name=db_name
    )
    
    store = MongoConfigStore(settings)
    
    # Verify Connection
    try:
        await store.client.admin.command('ping')
    except Exception:
        pytest.skip("MongoDB not available - skipping integration test", allow_module_level=True)
        
    yield store
    
    # Cleanup
    await store.client.drop_database(db_name)
    store.client.close()

@pytest.mark.asyncio
async def test_mongo_integration_workflow(real_mongo_store):
    store = real_mongo_store
    
    # 1. Create a Pipeline
    pipeline = Pipeline(
        name="integration-pipe",
        query="up",
        step="1m",
        context_window="1h",
        prediction_horizon="15m",
        model={"type": "local", "id": "integration-test"},
        output={"metric_prefix": "int_"}
    )
    
    # 2. Save
    await store.save_pipeline(pipeline)
    
    # 3. Get
    loaded = await store.get_pipeline("integration-pipe")
    assert loaded is not None
    assert loaded.name == "integration-pipe"
    assert loaded.model.id == "integration-test"
    
    # 4. List
    pipelines = await store.list_pipelines()
    assert len(pipelines) >= 1
    names = [p.name for p in pipelines]
    assert "integration-pipe" in names
    
    # 5. Delete
    deleted = await store.delete_pipeline("integration-pipe")
    assert deleted is True
    
    # 6. Verify Deletion
    missing = await store.get_pipeline("integration-pipe")
    assert missing is None
