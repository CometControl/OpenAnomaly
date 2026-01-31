import os
import sys
import django
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'openanomaly.config.settings')
os.environ['OPENANOMALY_CONFIG_FILE'] = 'config.yaml'

try:
    django.setup()
    from django.conf import settings
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DB_TYPE: {settings.DB_TYPE}")
    print(f"REDIS_URL: {settings.REDIS_URL}")
    print("Configuration loaded successfully!")
except Exception as e:
    print(f"Configuration failed: {e}")
    sys.exit(1)
