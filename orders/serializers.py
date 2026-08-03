from rest_framework import serializers

from .models import CargoOrder


class CargoOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CargoOrder
        fields = (
            "id",
            "customer",
            "origin_station",
            "destination_station",
            "cargo_size",
            "estimated_weight_kg",
            "notes",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("customer", "status", "created_at", "updated_at")
