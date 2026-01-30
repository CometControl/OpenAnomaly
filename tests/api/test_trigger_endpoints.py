import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from openanomaly.main import app

client = TestClient(app)

@pytest.fixture
def mock_celery():
    with patch("openanomaly.main.run_inference_task") as inference_mock, \
         patch("openanomaly.main.run_training_task") as training_mock:
        
        # Setup mock returns
        inference_task = MagicMock()
        inference_task.id = "inference-task-123"
        inference_mock.delay.return_value = inference_task
        
        training_task = MagicMock()
        training_task.id = "training-task-456"
        training_mock.delay.return_value = training_task
        
        yield inference_mock, training_mock

@pytest.fixture
def mock_inference_loop():
    with patch("openanomaly.main.InferenceLoop") as loop_mock:
        instance = loop_mock.return_value
        instance.run_pipeline = AsyncMock() 
        yield loop_mock

@pytest.fixture
def mock_training_loop():
    with patch("openanomaly.pipelines.training.TrainingLoop") as loop_mock:
        instance = loop_mock.return_value
        instance.run_training = AsyncMock(return_value="new-model-id")
        yield loop_mock

def test_trigger_inference_endpoint(mock_celery):
    inference_mock, _ = mock_celery
    
    response = client.post("/pipelines/test-pipeline/inference")
    
    assert response.status_code == 200
    assert response.json()["task_id"] == "inference-task-123"
    inference_mock.delay.assert_called_once_with("test-pipeline")

def test_trigger_training_endpoint(mock_celery):
    _, training_mock = mock_celery
    
    response = client.post("/pipelines/test-pipeline/train")
    
    assert response.status_code == 200
    assert response.json()["task_id"] == "training-task-456"
    training_mock.delay.assert_called_once_with("test-pipeline")

def test_execute_inference_endpoint(mock_inference_loop):
    payload = {
        "name": "adhoc",
        "query": "up",
        "step": "1m",
        "context_window": "1h",
        "prediction_horizon": "15m",
        "mode": "forecast_only",
        "model": {
            "type": "local",
            "id": "test/model"
        },
        "output": {
            "metric_prefix": "adhoc_"
        }
    }
    
    # We need to mock the async call await logic if we want deep integration test
    # But for controller test, we verify 200 OK and Service Instantiation
    # Since endpoint is async, TestClient handles async loop
    
    with patch("openanomaly.main.PrometheusAdapter"), \
         patch("openanomaly.common.adapters.models.chronos.adapter.ChronosAdapter"): # source patch because lazy import
         
        response = client.post("/execute/inference", json=payload)
        
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_execute_training_endpoint(mock_training_loop):
    payload = {
        "name": "adhoc",
        "query": "up",
        "step": "1m",
        "context_window": "1h",
        "prediction_horizon": "15m",
        "mode": "forecast_only",
        "model": {
            "type": "remote",
            "endpoint": "http://remote/predict",
            "serialization_format": "json"
        },
        "training": {
            "endpoint": "http://remote/train"
        },
        "output": {
            "metric_prefix": "adhoc_"
        }
    }

    with patch("openanomaly.main.PrometheusAdapter"), \
         patch("openanomaly.adapters.models.remote.RemoteModelAdapter"):
         
        response = client.post("/execute/train", json=payload)
        
    assert response.status_code == 200
    assert response.json()["model_id"] == "new-model-id"
