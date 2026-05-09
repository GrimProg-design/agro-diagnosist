"""
АгроДиагност — DRF serializers.
"""
from __future__ import annotations

from rest_framework import serializers


class DiagnosisRequestSerializer(serializers.Serializer):
    """Validates the incoming multipart/form-data diagnosis request."""

    image     = serializers.ImageField(required=True)
    crop_type = serializers.CharField(max_length=60, required=True)

    def validate_crop_type(self, value: str) -> str:
        from apps.diagnosis.models import Crop

        if not Crop.objects.filter(code=value).exists():
            raise serializers.ValidationError(
                f"Культура с кодом '{value}' не найдена в базе данных."
            )
        return value


class DiagnosisResultSerializer(serializers.Serializer):
    """Serializes the final diagnosis result sent to the frontend."""

    diagnosis       = serializers.CharField()
    confidence      = serializers.IntegerField(min_value=0, max_value=100)
    severity        = serializers.CharField()
    symptoms        = serializers.ListField(child=serializers.CharField())
    recommendations = serializers.ListField(child=serializers.CharField())
    cropType        = serializers.CharField()
    analyzedAt      = serializers.DateTimeField()
