import pytest
from django.test import TransactionTestCase
from openanomaly.pipelines.models import Pipeline
from openanomaly.config.django_store import DjangoConfigStore


@pytest.mark.integration
class PipelinePersistenceTest(TransactionTestCase):
    def setUp(self):
        self.store = DjangoConfigStore()

    async def test_persistence_flow(self):
        # 1. Create (ORM)
        pipeline_name = "test_django_persistence"
        defaults = {
            "query": "up",
            "mode": "forecast_only",
            "model_config": {"type": "local"},
            "forecast_schedule": "*/5 * * * *"
        }
        
        await Pipeline.objects.acreate(name=pipeline_name, **defaults)
        
        # 2. Retrieve (ConfigStore)
        p = await self.store.get_pipeline(pipeline_name)
        self.assertIsNotNone(p)
        self.assertEqual(p.name, pipeline_name)
        self.assertEqual(p.query, "up")
        
        # 3. Update (ORM)
        p_model = await Pipeline.objects.aget(name=pipeline_name)
        p_model.query = "up + 1"
        await p_model.asave()
        
        # 4. Retrieve Updated (ConfigStore)
        p_updated = await self.store.get_pipeline(pipeline_name)
        self.assertEqual(p_updated.query, "up + 1")
        
        # 5. List
        pipelines = await self.store.list_pipelines()
        names = [pl.name for pl in pipelines]
        self.assertIn(pipeline_name, names)

    async def test_deletion_flow(self):
        pipeline_name = "test_django_delete"
        await Pipeline.objects.acreate(name=pipeline_name, query="foo")
        
        # Verify exists
        self.assertTrue(await Pipeline.objects.filter(name=pipeline_name).aexists())
        
        # Delete via Store
        deleted = await self.store.delete_pipeline(pipeline_name)
        self.assertTrue(deleted)
        
        # Verify gone
        self.assertFalse(await Pipeline.objects.filter(name=pipeline_name).aexists())
