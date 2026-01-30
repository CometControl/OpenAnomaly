import os
import pytest
from openanomaly.adapters.config.settings import SystemSettings
from openanomaly.adapters.config.settings_loader import load_settings

def test_system_settings_defaults():
    settings = SystemSettings()
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.victoriametrics_url == "http://localhost:8428"
    assert settings.get_write_url() == "http://localhost:8428/api/v1/write"
    assert settings.pipelines_file == "pipelines.yaml"

def test_system_settings_overrides():
    settings = SystemSettings(
        victoriametrics_url="http://vm:8428",
        victoriametrics_write_url="http://vm:8428/write"
    )
    assert settings.get_write_url() == "http://vm:8428/write"

def test_load_settings_from_env(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://custom:6379/1")
    monkeypatch.setenv("VICTORIAMETRICS_URL", "http://custom:8428")
    
    settings = load_settings(path="non_existent.yaml")
    
    assert settings.redis_url == "redis://custom:6379/1"
    assert settings.victoriametrics_url == "http://custom:8428"

def test_load_settings_from_file(tmp_path):
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("""
redis_url: "redis://file:6379/0"
pipelines_file: "custom_pipelines.yaml"
    """)
    
    settings = load_settings(path=str(config_file))
    
    assert settings.redis_url == "redis://file:6379/0"
    assert settings.pipelines_file == "custom_pipelines.yaml"
    # Defaults preserved
    assert settings.victoriametrics_url == "http://localhost:8428"

def test_load_settings_env_overrides_file(tmp_path, monkeypatch):
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text('redis_url: "redis://file:6379/0"')
    
    monkeypatch.setenv("REDIS_URL", "redis://env:6379/0")
    
    settings = load_settings(path=str(config_file))
    
    # Env var should hold precedence
    assert settings.redis_url == "redis://env:6379/0"
