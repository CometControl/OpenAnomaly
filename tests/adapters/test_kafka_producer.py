"""
Tests for Kafka Producer Adapter
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from openanomaly.common.adapters.kafka_producer import KafkaProducerAdapter


pytestmark = pytest.mark.unit  # Mark all tests in this module as unit tests


@pytest.fixture
def mock_producer():
    """Mock Kafka Producer."""
    with patch('openanomaly.common.adapters.kafka_producer.Producer') as MockProducer:
        producer_instance = MagicMock()
        MockProducer.return_value = producer_instance
        yield producer_instance


def test_kafka_producer_initialization():
    """Test KafkaProducerAdapter initialization."""
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    assert adapter.bootstrap_servers == "localhost:9092"
    assert adapter.producer is None  # Lazy initialization


def test_kafka_producer_lazy_init(mock_producer):
    """Test lazy initialization of Kafka producer."""
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    producer = adapter._get_producer()
    
    assert producer is not None
    assert adapter.producer is not None


def test_publish_message(mock_producer):
    """Test publishing a generic message."""
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    
    message = {
        "event_type": "training_started",
        "pipeline_name": "test-pipeline",
        "model_id": "chronos-small"
    }
    
    adapter.publish_message(
        topic="training-events",
        message=message,
        key="test-pipeline"
    )
    
    # Verify producer.produce was called
    assert mock_producer.produce.called
    call_kwargs = mock_producer.produce.call_args[1]
    
    assert call_kwargs['topic'] == "training-events"
    assert call_kwargs['key'] == b"test-pipeline"
    
    # Verify message content
    published_message = json.loads(call_kwargs['value'].decode('utf-8'))
    assert published_message['event_type'] == "training_started"
    assert published_message['pipeline_name'] == "test-pipeline"
    assert published_message['model_id'] == "chronos-small"


def test_publish_message_without_key(mock_producer):
    """Test publishing message without key."""
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    
    message = {"event": "test"}
    
    adapter.publish_message(
        topic="test-topic",
        message=message,
        key=None
    )
    
    call_kwargs = mock_producer.produce.call_args[1]
    assert call_kwargs['key'] is None


def test_publish_custom_message_structure(mock_producer):
    """Test publishing custom message structure."""
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    
    # Custom CloudEvents-like structure
    message = {
        "specversion": "1.0",
        "type": "com.openanomaly.training.completed",
        "source": "/pipelines/my-pipeline",
        "data": {
            "model_id": "new-model-123",
            "duration_seconds": 125.5
        }
    }
    
    adapter.publish_message(
        topic="cloudevents",
        message=message,
        key="my-pipeline"
    )
    
    # Verify message content
    call_kwargs = mock_producer.produce.call_args[1]
    published_message = json.loads(call_kwargs['value'].decode('utf-8'))
    
    assert published_message['specversion'] == "1.0"
    assert published_message['type'] == "com.openanomaly.training.completed"
    assert published_message['data']['duration_seconds'] == 125.5


def test_kafka_error_handling(mock_producer):
    """Test that Kafka errors don't break execution."""
    mock_producer.produce.side_effect = Exception("Kafka connection failed")
    
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    
    # Should not raise exception
    adapter.publish_message(
        topic="test-topic",
        message={"event": "test"},
        key="test-key"
    )


def test_flush(mock_producer):
    """Test flushing pending messages."""
    mock_producer.flush.return_value = 0
    
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    adapter._get_producer()  # Initialize
    
    adapter.flush(timeout=5.0)
    
    mock_producer.flush.assert_called_once_with(5.0)


def test_flush_with_remaining_messages(mock_producer):
    """Test flush warning when messages remain."""
    mock_producer.flush.return_value = 5  # 5 messages not delivered
    
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    adapter._get_producer()  # Initialize
    
    adapter.flush(timeout=5.0)
    
    mock_producer.flush.assert_called_once_with(5.0)


def test_close(mock_producer):
    """Test closing the producer."""
    mock_producer.flush.return_value = 0
    
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    adapter._get_producer()  # Initialize
    
    adapter.close()
    
    mock_producer.flush.assert_called_once()
    assert adapter.producer is None


def test_json_serialization(mock_producer):
    """Test JSON serialization of complex types."""
    adapter = KafkaProducerAdapter(bootstrap_servers="localhost:9092")
    
    message = {
        "string": "test",
        "number": 123,
        "float": 45.67,
        "boolean": True,
        "null": None,
        "array": [1, 2, 3],
        "nested": {"key": "value"}
    }
    
    adapter.publish_message(
        topic="test-topic",
        message=message,
        key="test"
    )
    
    call_kwargs = mock_producer.produce.call_args[1]
    published_message = json.loads(call_kwargs['value'].decode('utf-8'))
    
    assert published_message == message
