
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'openanomaly.pipelines'

    def ready(self):
        import openanomaly.pipelines.signals
