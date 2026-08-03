from rest_framework import serializers

from .models import CargoTrip


class CargoTripSerializer(serializers.ModelSerializer):
    class Meta:
        model = CargoTrip
        fields = (
            "id",
            "order",
            "leg_type",
            "driver",
            "vehicle_type",
            "pickup_latitude",
            "pickup_longitude",
            "pickup_address_text",
            "destination_station",
            "distance_km",
            "fare_rate",
            "fare_amount",
            "status",
            "requested_at",
            "driver_assigned_at",
            "arrived_at_pickup_at",
            "picked_up_at",
            "delivered_at",
            "cancelled_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "driver",
            "fare_rate",
            "fare_amount",
            "status",
            "requested_at",
            "driver_assigned_at",
            "arrived_at_pickup_at",
            "picked_up_at",
            "delivered_at",
            "cancelled_at",
            "created_at",
            "updated_at",
        )
