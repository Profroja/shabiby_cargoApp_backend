from rest_framework import serializers

from .models import CargoSize


class CargoSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CargoSize
        fields = ("id", "name", "max_weight_kg", "description", "is_active")
