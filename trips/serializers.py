from rest_framework import serializers

from stations.views import _fetch_cargo_centers

from .models import CargoTrip


def _get_center_map():
    data = _fetch_cargo_centers(active_only=False)
    if not data:
        return {}
    return {str(item.get("id")): item for item in data}


class CargoTripSerializer(serializers.ModelSerializer):
    destination_station = serializers.CharField()
    vehicle_type = serializers.IntegerField()

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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        centers = self.context.get("_center_map")
        if centers is None:
            centers = _get_center_map()
        c = centers.get(str(instance.destination_station))
        if c:
            ret["destination_station"] = {
                "id": c.get("id"),
                "name": c.get("center_name", ""),
                "center_name": c.get("center_name", ""),
                "location": c.get("location", ""),
                "branch_code": c.get("branch_code", ""),
                "is_active": c.get("is_active", True),
            }
        else:
            ret["destination_station"] = {
                "id": instance.destination_station,
                "name": "",
                "center_name": "",
                "branch_code": "",
                "is_active": True,
            }
        return ret
