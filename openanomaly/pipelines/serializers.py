from rest_framework import serializers
from openanomaly.pipelines.models import Pipeline


class PipelineSerializer(serializers.ModelSerializer):
    """
    Serializer for Pipeline model with full CRUD support.
    Automatically handles all fields and validation.
    """
    active_tasks = serializers.ReadOnlyField()
    is_fully_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Pipeline
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
