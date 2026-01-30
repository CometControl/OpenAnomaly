
import os
import environ
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Remove environ definition as we use custom get_config

# Reading .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Support loading from a YAML config file (e.g., ConfigMap)
# Precedence: Env Var > YAML Config > Default
import yaml

CONFIG_FILE = os.environ.get('OPENANOMALY_CONFIG_FILE')
yaml_config = {}
if CONFIG_FILE and os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            yaml_config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Failed to load config file {CONFIG_FILE}: {e}")

def get_config(key, default=None, cast=None):
    # 1. Environment Variable
    # 2. YAML Config
    # 3. Default
    val = os.environ.get(key)
    if val is None:
        # Try finding in YAML (lowercase key without prefix)
        # e.g. OPENANOMALY_DEBUG -> debug
        simple_key = key.replace('OPENANOMALY_', '').lower()
        val = yaml_config.get(simple_key)
    
    if val is None:
        return default
        
    if cast:
        if cast is bool:
            if isinstance(val, bool): return val
            return str(val).lower() in ('true', '1', 't', 'y', 'yes')
        return cast(val)
    return val

DEBUG = get_config('OPENANOMALY_DEBUG', False, bool)
SECRET_KEY = get_config('OPENANOMALY_SECRET_KEY', 'insecure-default-key-for-dev', str)

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.sessions', # Needed for SQLite mostly, fails without Auth in some cases, leaving for now
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django_mongodb_backend' added conditionally
    'openanomaly.common',
    'openanomaly.pipelines',
    'openanomaly.common.adapters.schedulers',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add WhiteNoise for static files
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

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DB_TYPE = get_config('OPENANOMALY_DATABASE_TYPE', 'mongodb')

if DB_TYPE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Default to MongoDB
    DATABASES = {
        'default': {
            'ENGINE': 'django_mongodb_backend',
            'NAME': get_config('OPENANOMALY_MONGO_DB_NAME', 'openanomaly'),
            'CLIENT': {
                'host': get_config('OPENANOMALY_MONGO_URL', 'mongodb://localhost:27017'),
            },
        }
    }
# Always enable Auth/Admin apps for Django admin panel access
INSTALLED_APPS.insert(0, 'django.contrib.admin')
INSTALLED_APPS.insert(1, 'django.contrib.auth')
INSTALLED_APPS.insert(2, 'django.contrib.contenttypes')

if get_config('OPENANOMALY_DATABASE_TYPE', 'mongodb') != 'sqlite':
    # MongoDB Mode - insert MongoDB backend
    INSTALLED_APPS.insert(6, 'django_mongodb_backend')
    

# ... (omitted standard settings for brevity, keeping them as is)

# --- OpenAnomaly Custom Settings ---
REDIS_URL = get_config('OPENANOMALY_REDIS_URL', 'redis://localhost:6379/0')
PROMETHEUS_URL = get_config('OPENANOMALY_PROMETHEUS_URL', 'http://localhost:8428')
PROMETHEUS_WRITE_URL = get_config('OPENANOMALY_PROMETHEUS_WRITE_URL', None)
DATABASE_TYPE = get_config('OPENANOMALY_DATABASE_TYPE', 'mongodb', str) # mongodb or sqlite
PIPELINES_FILE = get_config('OPENANOMALY_PIPELINES_FILE', 'pipelines.yaml')
CONFIG_STORE_TYPE = get_config('OPENANOMALY_CONFIG_STORE_TYPE', 'yaml')

def get_write_url():
    if PROMETHEUS_WRITE_URL:
        return PROMETHEUS_WRITE_URL
    return f"{PROMETHEUS_URL}/api/v1/write"

# Celery Configuration
CELERY_BROKER_URL = get_config('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = get_config('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_TIMEZONE = "UTC"

if get_config('OPENANOMALY_DATABASE_TYPE', 'mongodb') == 'sqlite':
    DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
else:
    DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'

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
