import os
import yaml
from pathlib import Path
from openanomaly.config.schema import AppConfig

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- Configuration Loading ---
CONFIG_FILE = os.environ.get('OPENANOMALY_CONFIG_FILE', 'config.yaml')
config_path = BASE_DIR / CONFIG_FILE

if not config_path.exists():
    print(f"Warning: Config file {config_path} not found. Using defaults.")
    config_data = {}
else:
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        config_data = {}

# Validate and Load Config
try:
    app_config = AppConfig(**config_data)
except Exception as e:
    print(f"Configuration Validation Error: {e}")
    # Fallback to default if validation fails hard, or re-raise? 
    # For now, let's crash early if config is invalid to avoid weird states
    raise e

# --- Django Settings ---
DEBUG = app_config.django.debug
SECRET_KEY = app_config.django.secret_key
ALLOWED_HOSTS = app_config.django.allowed_hosts

# Application definition
INSTALLED_APPS = [
    # Always enable Auth/Admin apps for Django admin panel access
    'django.contrib.admin',
    # Use custom AuthConfig to ensure ObjectIdAutoField is used for User model on MongoDB
    'openanomaly.config.auth_config.MongoAuthConfig',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'openanomaly.common',
    'openanomaly.pipelines',
    'openanomaly.common.adapters.schedulers',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'openanomaly.config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'openanomaly.config.wsgi.application'
ASGI_APPLICATION = 'openanomaly.config.asgi.application'

# Database Setup
DB_TYPE = app_config.django.database_type

if DB_TYPE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
else:
    # MongoDB
    import urllib.parse
    mongo_url = app_config.mongo.url
    
    # Parse URL for django-mongodb-backend
    try:
        parsed_url = urllib.parse.urlparse(mongo_url)
        mongo_host = parsed_url.hostname or 'localhost'
        mongo_port = parsed_url.port or 27017
    except Exception:
        mongo_host = 'localhost'
        mongo_port = 27017

    DATABASES = {
        'default': {
            'ENGINE': 'django_mongodb_backend',
            'NAME': app_config.mongo.db_name,
            'HOST': mongo_host,
            'PORT': mongo_port,
        }
    }
    DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'
    
    # Add MongoDB backend app
    INSTALLED_APPS.append('django_mongodb_backend')

    # Disable migrations for system apps
    MIGRATION_MODULES = {
        'admin': None,
        'auth': None,
        'contenttypes': None,
        'sessions': None,
        'pipelines': None,
    }
    SILENCED_SYSTEM_CHECKS = ['mongodb.E001']

# --- Custom OpenAnomaly Settings ---
REDIS_URL = app_config.redis.url
PROMETHEUS_URL = app_config.prometheus.url
PROMETHEUS_WRITE_URL = app_config.prometheus.write_url
DATABASE_TYPE = DB_TYPE
PIPELINES_FILE = app_config.pipelines_file
CONFIG_STORE_TYPE = app_config.config_store_type

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = 'redbeat.RedBeatScheduler'
CELERY_REDBEAT_REDIS_URL = REDIS_URL

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
