import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from openanomaly.core.domain.settings import SystemSettings
from openanomaly.core.domain.pipeline import Pipeline
# We can't import MongoConfigStore if motor is not installed and we are in strict env
# so we mock sys.modules or rely on the code structure.
# But for unit test, let's assume we can patch it.

# Mock motor module before importing
import sys
sys.modules["motor"] = MagicMock()
sys.modules["motor.motor_asyncio"] = MagicMock()

# Now we can import (or import inside test)
from openanomaly.adapters.config.mongo_store import MongoConfigStore

@pytest.fixture
def mock_settings():
    return SystemSettings(
        config_store_type="mongo",
        mongo_url="mongodb://test:27017",
        mongo_db_name="test_db"
    )

@pytest.fixture
def mock_mongo_client():
    with patch("openanomaly.adapters.config.mongo_store.AsyncIOMotorClient") as client_cls:
        client = client_cls.return_value
        db = client.__getitem__.return_value # client["db"]
        collection = db.__getitem__.return_value # db["collection"]
        yield client_cls, collection

@pytest.mark.asyncio
async def test_get_pipeline_found(mock_settings, mock_mongo_client):
    _, collection = mock_mongo_client
    
    # Mock find_one return
    pipeline_data = {
        "name": "test-pipeline",
        "query": "up",
        "step": "1m",
        "context_window": "1h",
        "prediction_horizon": "15m",
        "mode": "forecast_only",
        "model": {"type": "local", "id": "test"},
        "output": {"metric_prefix": "pred_"}
    }
    collection.find_one = AsyncMock(return_value=pipeline_data)
    
    store = MongoConfigStore(mock_settings)
    pipeline = await store.get_pipeline("test-pipeline")
    
    assert pipeline is not None
    assert pipeline.name == "test-pipeline"
    collection.find_one.assert_called_with({"name": "test-pipeline"})

@pytest.mark.asyncio
async def test_get_pipeline_not_found(mock_settings, mock_mongo_client):
    _, collection = mock_mongo_client
    collection.find_one = AsyncMock(return_value=None)
    
    store = MongoConfigStore(mock_settings)
    pipeline = await store.get_pipeline("missing")
    
    assert pipeline is None

@pytest.mark.asyncio
async def test_save_pipeline(mock_settings, mock_mongo_client):
    _, collection = mock_mongo_client
    collection.replace_one = AsyncMock()
    
    pipeline = Pipeline(
        name="new-pipeline",
        query="up",
        step="1m",
        context_window="1h",
        prediction_horizon="1m",
        model={"type": "local", "id": "foo"},
        output={"metric_prefix": "bar_"}
    )
    
    store = MongoConfigStore(mock_settings)
    await store.save_pipeline(pipeline)
    
    collection.replace_one.assert_called_once()
    args, kwargs = collection.replace_one.call_args
    assert args[0] == {"name": "new-pipeline"}
    assert kwargs["upsert"] is True
