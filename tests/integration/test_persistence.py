
import pytest
from openanomaly.pipelines.models import Pipeline
from openanomaly.config.django_store import DjangoConfigStore

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_pipeline_persistence():
    """
    Test creating, retrieving, and updating valid pipelines via ORM and ConfigStore.
    """
    store = DjangoConfigStore()
    
    # 1. Create (ORM)
    pipeline_name = "test_persistence_pipeline"
    defaults = {
        "query": "up",
        "mode": "forecast_only",
        "model_config": {"type": "local"},
        "forecast_schedule": "*/5 * * * *"
    }
    
    await Pipeline.objects.acreate(name=pipeline_name, **defaults)
    
    # 2. Retrieve (ConfigStore)
    p = await store.get_pipeline(pipeline_name)
    assert p is not None
    assert p.name == pipeline_name
    assert p.query == "up"
    
    # 3. Update (ORM)
    p_model = await Pipeline.objects.aget(name=pipeline_name)
    p_model.query = "up + 1"
    await p_model.asave()
    
    # 4. Retrieve Updated (ConfigStore)
    p_updated = await store.get_pipeline(pipeline_name)
    assert p_updated.query == "up + 1"
    
    # 5. List
    pipelines = await store.list_pipelines()
    names = [pl.name for pl in pipelines]
    assert pipeline_name in names

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_pipeline_deletion():
    pipeline_name = "test_delete_pipeline"
    await Pipeline.objects.acreate(name=pipeline_name, query="foo")
    
    # Verify exists
    assert await Pipeline.objects.filter(name=pipeline_name).aexists()
    
    # Delete
    p = await Pipeline.objects.aget(name=pipeline_name)
    await p.adelete()
    
    # Verify gone
    assert not await Pipeline.objects.filter(name=pipeline_name).aexists()
