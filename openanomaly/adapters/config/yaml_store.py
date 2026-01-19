"""
YAML Config Store Adapter - File-based pipeline configuration.

Loads pipeline definitions from a YAML file.
"""

from pathlib import Path
from typing import Any

import yaml

from openanomaly.core.domain.pipeline import (
    ModelConfig,
    Pipeline,
)
from openanomaly.core.ports.config_store import ConfigStore


class YamlConfigStore(ConfigStore):
    """
    Config store that reads pipelines from a YAML file.
    """
    
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self._pipelines: dict[str, Pipeline] = {}
        self._loaded = False
    
    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load_pipelines()
            self._loaded = True
    
    def _load_pipelines(self) -> None:
        if not self.config_path.exists():
            return
        
        with open(self.config_path) as f:
            data = yaml.safe_load(f) or {}
        
        for pipeline_data in data.get("pipelines", []):
            try:
                pipeline = Pipeline(**pipeline_data)
                self._pipelines[pipeline.name] = pipeline
            except Exception as e:
                # In a real app, use logging
                print(f"Error loading pipeline: {e}")
    
    async def list_pipelines(self) -> list[Pipeline]:
        self._ensure_loaded()
        return list(self._pipelines.values())
    
    async def get_pipeline(self, name: str) -> Pipeline | None:
        self._ensure_loaded()
        return self._pipelines.get(name)
    
    async def save_pipeline(self, pipeline: Pipeline) -> None:
        self._ensure_loaded()
        self._pipelines[pipeline.name] = pipeline
        await self._save_to_file()
    
    async def delete_pipeline(self, name: str) -> bool:
        self._ensure_loaded()
        if name in self._pipelines:
            del self._pipelines[name]
            await self._save_to_file()
            return True
        return False
    
    async def _save_to_file(self) -> None:
        # Convert pipelines using Pydantic's model_dump
        pipelines_data = [
            p.model_dump(mode="json") 
            for p in self._pipelines.values()
        ]
        
        with open(self.config_path, "w") as f:
            yaml.dump({"pipelines": pipelines_data}, f, default_flow_style=False)
