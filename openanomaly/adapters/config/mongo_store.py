import logging
from motor.motor_asyncio import AsyncIOMotorClient
from openanomaly.core.ports.config_store import ConfigStore
from openanomaly.core.domain.pipeline import Pipeline
from openanomaly.core.domain.settings import SystemSettings

logger = logging.getLogger(__name__)

class MongoConfigStore(ConfigStore):
    """
    MongoDB-backed implementation of ConfigStore.
    Stores pipeline configurations as documents in a MongoDB collection.
    """
    
    def __init__(self, settings: SystemSettings):
        self.settings = settings
        self.client = AsyncIOMotorClient(settings.mongo_url)
        self.db = self.client[settings.mongo_db_name]
        self.collection = self.db["pipelines"]
        
    async def list_pipelines(self) -> list[Pipeline]:
        """List all configured pipelines."""
        pipelines = []
        async for doc in self.collection.find():
            try:
                # _id is typically the name, but we check if we stored it as 'name' field too
                # or if we need to map _id to name.
                # Let's assume we store the whole Pipeline model, so it has 'name'.
                if "_id" in doc: 
                    del doc["_id"] # Pydantic doesn't expect _id
                
                pipelines.append(Pipeline(**doc))
            except Exception as e:
                logger.error(f"Failed to parse pipeline document: {e}")
        return pipelines
    
    async def get_pipeline(self, name: str) -> Pipeline | None:
        """Get a specific pipeline by name."""
        doc = await self.collection.find_one({"name": name})
        if not doc:
            return None
            
        if "_id" in doc:
            del doc["_id"]
            
        try:
            return Pipeline(**doc)
        except Exception as e:
            logger.error(f"Failed to parse pipeline '{name}': {e}")
            return None
    
    async def save_pipeline(self, pipeline: Pipeline) -> None:
        """Save or update a pipeline."""
        data = pipeline.model_dump(mode="json")
        # Upsert based on name
        await self.collection.replace_one(
            {"name": pipeline.name},
            data,
            upsert=True
        )
    
    async def delete_pipeline(self, name: str) -> bool:
        """Delete a pipeline by name."""
        result = await self.collection.delete_one({"name": name})
        return result.deleted_count > 0
