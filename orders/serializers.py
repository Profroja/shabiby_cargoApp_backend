from rest_framework import serializers

from stations.views import _fetch_cargo_centers

from .models import CargoOrder


def _get_center_map():
    data = _fetch_cargo_centers(active_only=False)
    if not data:
        return {}
    return {str(item.get("id")): item for item in data}


class CargoOrderSerializer(serializers.ModelSerializer):
    origin_station = serializers.CharField()
    destination_station = serializers.CharField()

    class Meta:
        model = CargoOrder
        fields = (
            "id",
            "customer",
            "origin_station",
            "destination_station",
            "cargo_size",
            "estimated_weight_kg",
            "description",
            "notes",
            "receiver_name",
            "receiver_phone",
            "receiver_address",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("customer", "status", "created_at", "updated_at")

    def _get_center(self, station_id, centers):
        c = centers.get(str(station_id))
        if c:
            return {
                "id": c.get("id"),
                "name": c.get("center_name", ""),
                "center_name": c.get("center_name", ""),
                "location": c.get("location", ""),
                "branch_code": c.get("branch_code", ""),
                "is_active": c.get("is_active", True),
            }
        return {"id": station_id, "name": "", "center_name": "", "branch_code": "", "is_active": True}

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        centers = self.context.get("_center_map")
        if centers is None:
            centers = _get_center_map()
        ret["origin_station"] = self._get_center(instance.origin_station, centers)
        ret["destination_station"] = self._get_center(instance.destination_station, centers)
        return ret
