"""
Kafka Producer Adapter for OpenAnomaly.

Provides message production capabilities for publishing training events to Kafka topics.
"""

import json
import logging
from datetime import datetime
from typing import Any, Literal
from confluent_kafka import Producer
from confluent_kafka import KafkaException

logger = logging.getLogger(__name__)


class KafkaProducerAdapter:
    """
    Adapter for producing messages to Kafka topics.
    
    This adapter provides a simple interface for publishing training lifecycle
    events to Kafka with proper error handling and serialization.
    """
    
    def __init__(self, bootstrap_servers: str):
        """
        Initialize the Kafka producer.
        
        Args:
            bootstrap_servers: Comma-separated list of Kafka broker addresses
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        
    def _get_producer(self) -> Producer:
        """Lazy initialization of Kafka producer."""
        if self.producer is None:
            config = {
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': 'openanomaly-training',
                'acks': 'all',  # Wait for all replicas
                'retries': 3,
                'max.in.flight.requests.per.connection': 1,
            }
            self.producer = Producer(config)
        return self.producer
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery reports."""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
    
    def publish_message(
        self,
        topic: str,
        message: dict[str, Any],
        key: str | None = None,
    ):
        """
        Publish a generic message to Kafka.
        
        Args:
            topic: Kafka topic to publish to
            message: Message payload as dictionary (will be JSON serialized)
            key: Optional message key for partitioning
        """
        try:
            # Serialize to JSON
            message_json = json.dumps(message)
            
            # Produce message
            producer = self._get_producer()
            producer.produce(
                topic=topic,
                value=message_json.encode('utf-8'),
                key=key.encode('utf-8') if key else None,
                callback=self._delivery_callback
            )
            
            # Trigger delivery callbacks
            producer.poll(0)
            
            logger.info(f"Published message to topic '{topic}' with key '{key}'")
            
        except KafkaException as e:
            logger.error(f"Failed to publish message: {e}")
            # Don't raise - we don't want Kafka failures to break training
        except Exception as e:
            logger.error(f"Unexpected error publishing to Kafka: {e}")

    
    def flush(self, timeout: float = 10.0):
        """
        Wait for all messages to be delivered.
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        if self.producer:
            remaining = self.producer.flush(timeout)
            if remaining > 0:
                logger.warning(f"{remaining} messages were not delivered within timeout")
    
    def close(self):
        """Close the producer and flush remaining messages."""
        if self.producer:
            self.producer.flush(10.0)
            self.producer = None
