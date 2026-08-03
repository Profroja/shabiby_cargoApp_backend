from rest_framework import serializers

from .models import FareRate


class FareRateSerializer(serializers.ModelSerializer):
    vehicle_type_name = serializers.CharField(source="vehicle_type.name", read_only=True)
    vehicle_type_display = serializers.CharField(
        source="vehicle_type.display_name", read_only=True
    )

    class Meta:
        model = FareRate
        fields = (
            "id",
            "zone",
            "vehicle_type",
            "vehicle_type_name",
            "vehicle_type_display",
            "base_fare",
            "rate_per_km",
            "min_fare",
            "currency",
            "effective_from",
            "effective_to",
        )
