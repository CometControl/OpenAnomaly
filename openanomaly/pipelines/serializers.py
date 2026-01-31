from rest_framework import serializers
from openanomaly.pipelines.models import Pipeline


class ObjectIdField(serializers.Field):
    """
    Custom field to serialize MongoDB ObjectId to string.
    """
    def to_representation(self, value):
        return str(value)
    
    def to_internal_value(self, data):
        return data


class PipelineSerializer(serializers.ModelSerializer):
    """
    Serializer for Pipeline model with full CRUD support.
    Automatically handles all fields and validation.
    """
    id = ObjectIdField(read_only=True)
    active_tasks = serializers.ReadOnlyField()
    is_fully_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Pipeline
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
