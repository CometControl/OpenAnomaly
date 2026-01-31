
from django.apps import AppConfig

class CoreConfig(AppConfig):
    name = 'openanomaly.pipelines'

    def ready(self):
        import openanomaly.pipelines.signals
