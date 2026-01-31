# Kafka Integration for Training Events

This guide explains how to configure pipelines to publish training events to Kafka with custom message structures.

## Configuration

Each pipeline can define its own Kafka message structure using templates:

```yaml
pipelines:
  - name: "my_pipeline"
    description: "Pipeline with custom Kafka messages"
    enabled: true
    query: "up"
    
    model:
      type: "local"
      id: "amazon/chronos-t5-small"
    
    training:
      enabled: true
      schedule: "0 0 * * *"
      window: "30d"
      
      # Kafka Configuration
      kafka_enabled: true
      kafka_bootstrap_servers: "your-kafka-broker:9092"
      kafka_topic: "training-events"
      kafka_message_key: "{pipeline_name}"  # Template for partitioning key
      
      # Custom message template (optional)
      kafka_message_template:
        event: "{event_type}"
        pipeline: "{pipeline_name}"
        model: "{model_id}"
        timestamp: "{timestamp}"  # Will be auto-injected
```

## Message Templates

The `kafka_message_template` defines the structure of messages sent to Kafka. 

### Template Variables

Available variables for substitution:
- `{event_type}` - training_started, training_completed, or training_failed
- `{pipeline_name}` - Name of the pipeline
- `{model_id}` - Model identifier
- `{training_window}` - Training data window (e.g., "30d")
- `{status}` - success or failed (for completed/failed events)
- `{duration_seconds}` - Training duration
- `{error}` - Error message (for failed events)

### Default Template

If `kafka_message_template` is not specified or empty, a default structure is used:

```json
{
  "event_type": "training_started|training_completed|training_failed",
  "timestamp": "2026-01-31T15:12:00Z",
  "pipeline_name": "my_pipeline",
  "model_id": "amazon/chronos-t5-small",
  "training_window": "30d",
  "status": "success|failed",
  "duration_seconds": 210.5,
  "error": null
}
```

## Testing

To verify messages are being sent:

```bash
# Consume messages from your Kafka topic
kafka-console-consumer \
  --bootstrap-server your-kafka-broker:9092 \
  --topic training-events \
  --from-beginning \
  --property print.key=true
```

## Error Handling

- Kafka failures do **not** stop training execution
- Errors are logged but training continues
- Producer automatically retries failed deliveries
- Messages are flushed before task completion to ensure delivery
