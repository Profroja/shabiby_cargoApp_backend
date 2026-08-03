from rest_framework import serializers

from .models import VehicleType


class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = ("id", "name", "display_name", "max_weight_kg", "is_active")
