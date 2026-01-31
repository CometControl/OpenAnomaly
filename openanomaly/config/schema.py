from typing import List, Optional, Literal
from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings

class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379/0"

class PrometheusSettings(BaseModel):
    url: str = "http://localhost:8428"
    write_url: Optional[str] = None

class DjangoSettings(BaseModel):
    debug: bool = False
    secret_key: str = "insecure-default-key-for-dev"
    allowed_hosts: List[str] = ["*"]
    database_type: Literal["mongodb", "sqlite"] = "mongodb"

class MongoSettings(BaseModel):
    url: str = "mongodb://localhost:27017"
    db_name: str = "openanomaly"

class AppConfig(BaseSettings):
    django: DjangoSettings = Field(default_factory=DjangoSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    prometheus: PrometheusSettings = Field(default_factory=PrometheusSettings)
    mongo: MongoSettings = Field(default_factory=MongoSettings)
    pipelines_file: str = "pipelines.yaml"
    config_store_type: str = "yaml"

    model_config = {
        "case_sensitive": False,
        "env_file": ".env",
        "extra": "ignore"
    }
