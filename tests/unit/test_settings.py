import os
import pytest
import yaml
from openanomaly.config.schema import AppConfig

def test_app_config_defaults():
    config = AppConfig()
    assert config.django.debug is False
    assert config.mongo.db_name == "openanomaly"
    assert config.redis.url == "redis://localhost:6379/0"

def test_app_config_from_yaml(tmp_path):
    config_content = {
        "django": {"debug": True},
        "mongo": {"db_name": "test_db"},
        "redis": {"url": "redis://custom:6379/1"}
    }
    
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)
        
    with open(config_file, 'r') as f:
        data = yaml.safe_load(f)
        
    config = AppConfig(**data)
    assert config.django.debug is True
    assert config.mongo.db_name == "test_db"
    assert config.redis.url == "redis://custom:6379/1"
    # defaults
    assert config.django.database_type == "mongodb"

