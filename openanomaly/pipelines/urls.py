
from django.urls import path
from . import views

urlpatterns = [
    path('pipelines/<str:pipeline_name>/forecast', views.trigger_forecast, name='trigger_forecast'),
    path('pipelines/<str:pipeline_name>/anomaly', views.trigger_anomaly_check, name='trigger_anomaly'),
    path('pipelines/<str:pipeline_name>/train', views.trigger_training, name='trigger_training'),
    path('execute/inference', views.execute_inference_view, name='execute_inference'),
    path('execute/train', views.execute_training_view, name='execute_training'),
    path('health', views.health_check, name='health_check'),
]
