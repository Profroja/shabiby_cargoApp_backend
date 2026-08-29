from rest_framework import serializers

from .models import DriverCommissionBand


class DriverCommissionBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverCommissionBand
        fields = (
            "id",
            "min_distance_km",
            "max_distance_km",
            "commission_percent",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")