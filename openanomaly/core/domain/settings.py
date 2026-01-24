from typing import Literal
from pydantic import BaseModel, Field

class SystemSettings(BaseModel):
    """
    Global system configuration settings.
    """
    config_store_type: Literal["yaml", "mongo"] = Field(default="yaml", description="Configuration store backend")
    
    # Common
    redis_url: str = Field(default="redis://localhost:6379/0", description="Celery broker and backend URL")
    
    # Timeseries DB
    victoriametrics_url: str = Field(default="http://localhost:8428", description="VictoriaMetrics base URL")
    victoriametrics_write_url: str | None = Field(default=None, description="VictoriaMetrics Remote Write URL")
    
    # YAML Store
    pipelines_file: str = Field(default="pipelines.yaml", description="Path to pipelines configuration file")
    
    # Mongo Store
    mongo_url: str = Field(default="mongodb://localhost:27017", description="MongoDB Connection URL")
    mongo_db_name: str = Field(default="openanomaly", description="MongoDB Database Name")

    def get_write_url(self) -> str:
        """Get effective write URL."""
        if self.victoriametrics_write_url:
            return self.victoriametrics_write_url
        return f"{self.victoriametrics_url}/api/v1/write"
