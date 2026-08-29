from rest_framework import serializers

from commissions.models import get_driver_commission
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
    pickup_latitude = serializers.DecimalField(
        max_digits=10, decimal_places=7, coerce_to_string=False
    )
    pickup_longitude = serializers.DecimalField(
        max_digits=10, decimal_places=7, coerce_to_string=False
    )
    distance_km = serializers.DecimalField(
        max_digits=8, decimal_places=2, coerce_to_string=False
    )
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
    shipping_fare = serializers.SerializerMethodField()
    origin_station_name = serializers.SerializerMethodField()
    driver_commission_percent = serializers.SerializerMethodField()
    driver_commission_amount = serializers.SerializerMethodField()
    cargo_description = serializers.SerializerMethodField()
    cargo_weight_kg = serializers.SerializerMethodField()
    cargo_size_name = serializers.SerializerMethodField()

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
            "shipping_fare",
            "origin_station_name",
            "driver_commission_percent",
            "driver_commission_amount",
            "cargo_description",
            "cargo_weight_kg",
            "cargo_size_name",
        )
        read_only_fields = (
            "driver",
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

    def get_shipping_fare(self, obj):
        if obj.order.shipping_fare:
            return str(obj.order.shipping_fare)
        return None

    def get_driver_commission_percent(self, obj):
        percent, _amount = get_driver_commission(obj.distance_km, obj.fare_amount)
        if percent is None:
            return None
        return str(percent)

    def get_driver_commission_amount(self, obj):
        _percent, amount = get_driver_commission(obj.distance_km, obj.fare_amount)
        if amount is None:
            return None
        return str(amount)

    def get_cargo_description(self, obj):
        return obj.order.description or ""

    def get_cargo_weight_kg(self, obj):
        if obj.order.estimated_weight_kg:
            return str(obj.order.estimated_weight_kg)
        return None

    def get_cargo_size_name(self, obj):
        from cargosizes.models import CargoSize
        try:
            cs = CargoSize.objects.get(id=obj.order.cargo_size)
            return cs.name
        except (CargoSize.DoesNotExist, ValueError, TypeError):
            return None

    def get_origin_station_name(self, obj):
        centers = _get_center_map()
        c = centers.get(str(obj.order.origin_station))
        if c:
            return c.get("center_name", "") or c.get("name", "")
        return obj.order.origin_station

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        centers = self.context.get("_center_map")
        if centers is None:
            centers = _get_center_map()
        c = centers.get(str(instance.destination_station))
        
        # Try to get coordinates from local CargoStation model
        latitude = None
        longitude = None
        try:
            from stations.models import CargoStation
            local_station = CargoStation.objects.filter(
                branch_code=c.get("branch_code") if c else None
            ).first()
            if local_station:
                latitude = float(local_station.latitude) if local_station.latitude else None
                longitude = float(local_station.longitude) if local_station.longitude else None
        except Exception:
            pass
        
        if c:
            ret["destination_station"] = {
                "id": c.get("id"),
                "name": c.get("center_name", ""),
                "center_name": c.get("center_name", ""),
                "location": c.get("location", ""),
                "branch_code": c.get("branch_code", ""),
                "is_active": c.get("is_active", True),
                "latitude": latitude,
                "longitude": longitude,
            }
        else:
            ret["destination_station"] = {
                "id": instance.destination_station,
                "name": "",
                "center_name": "",
                "branch_code": "",
                "is_active": True,
                "latitude": None,
                "longitude": None,
            }
        return ret
