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
    driver_name = serializers.SerializerMethodField()
    driver_phone = serializers.SerializerMethodField()
    driver_photo_url = serializers.SerializerMethodField()
    driver_latitude = serializers.SerializerMethodField()
    driver_longitude = serializers.SerializerMethodField()
    driver_rating = serializers.SerializerMethodField()
    driver_vehicle_name = serializers.SerializerMethodField()
    driver_vehicle_plate = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()

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
            "driver_name",
            "driver_phone",
            "driver_photo_url",
            "driver_latitude",
            "driver_longitude",
            "driver_rating",
            "driver_vehicle_name",
            "driver_vehicle_plate",
            "customer_name",
            "customer_phone",
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

    def get_driver_name(self, obj):
        if obj.driver:
            u = obj.driver.user
            return f"{u.first_name} {u.last_name}".strip()
        return None

    def get_driver_phone(self, obj):
        if obj.driver:
            return obj.driver.user.phone_number
        return None

    def get_driver_photo_url(self, obj):
        if obj.driver and obj.driver.profile_photo:
            from django.conf import settings
            return f"{settings.BASE_URL}/{obj.driver.profile_photo.url.lstrip('/')}"
        return None

    def get_driver_latitude(self, obj):
        if obj.driver and obj.driver.current_latitude:
            return float(obj.driver.current_latitude)
        return None

    def get_driver_longitude(self, obj):
        if obj.driver and obj.driver.current_longitude:
            return float(obj.driver.current_longitude)
        return None

    def get_driver_rating(self, obj):
        if obj.driver:
            return float(obj.driver.rating_avg)
        return None

    def get_driver_vehicle_name(self, obj):
        if obj.driver:
            return obj.driver.vehicle_name
        return None

    def get_driver_vehicle_plate(self, obj):
        if obj.driver:
            return obj.driver.license_plate
        return None

    def get_customer_name(self, obj):
        u = obj.order.customer
        return f"{u.first_name} {u.last_name}".strip()

    def get_customer_phone(self, obj):
        return obj.order.customer.phone_number

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
