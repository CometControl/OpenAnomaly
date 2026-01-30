
import logging
from django.conf import settings
from openanomaly.common.interfaces.config_store import ConfigStore

logger = logging.getLogger(__name__)

def get_config_store() -> ConfigStore:
    """
    Factory to create the config store. 
    Always uses DjangoConfigStore as we now rely on DB (SQLite/Mongo) seeded from YAML.
    """
    from openanomaly.config.django_store import DjangoConfigStore
    return DjangoConfigStore()
