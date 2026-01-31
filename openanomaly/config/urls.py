
from django.urls import path, include
from openanomaly.common import health

urlpatterns = [
    # Kubernetes health check endpoints
    path('healthz', health.healthz, name='healthz'),
    path('health', health.healthz, name='health'),
    path('readiness', health.readiness, name='readiness'),
    path('ready', health.readiness, name='ready'),
    path('startup', health.startup, name='startup'),
    path('', include('openanomaly.pipelines.urls')),
]

from django.conf import settings
if 'django.contrib.admin' in settings.INSTALLED_APPS:
    from django.contrib import admin
    urlpatterns.insert(0, path('admin/', admin.site.urls))
