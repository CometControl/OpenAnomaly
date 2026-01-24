import os
import yaml
from openanomaly.core.domain.settings import SystemSettings

def load_settings(path: str | None = None) -> SystemSettings:
    """
    Load system settings from a YAML file.
    Falls back to environment variables if file doesn't exist or is not provided.
    
    Args:
        path: Path to config.yaml. Defaults to OA_CONFIG_FILE env var or "config.yaml".
    """
    if path is None:
        path = os.getenv("OA_CONFIG_FILE", "config.yaml")

    config_data = {}
    
    # helper to check file existence
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            # If config file is corrupt, we might want to fail hard
            raise RuntimeError(f"Failed to load configuration from {path}: {e}")
    
    # Overlay/Fallback to Environment Variables (Optional but good for container overrides)
    # Strategy: Env vars take precedence OR fill missing? 
    # Usually: Env vars > File > Defaults.
    # Let's check for specific overrides
    
    if os.getenv("REDIS_URL"):
        config_data["redis_url"] = os.getenv("REDIS_URL")
        
    if os.getenv("VICTORIAMETRICS_URL"):
        config_data["victoriametrics_url"] = os.getenv("VICTORIAMETRICS_URL")
        
    if os.getenv("VICTORIAMETRICS_WRITE_URL"):
        config_data["victoriametrics_write_url"] = os.getenv("VICTORIAMETRICS_WRITE_URL")
        
    if os.getenv("OA_PIPELINES_FILE"):
        config_data["pipelines_file"] = os.getenv("OA_PIPELINES_FILE")

    return SystemSettings(**config_data)
