from django.contrib import admin

from stations.views import _fetch_cargo_centers

from .models import CargoOrder


def _get_station_name_map():
    """Return {station_id: center_name} from the external cargo centers API."""
    data = _fetch_cargo_centers(active_only=False)
    if not data:
        return {}
    return {
        str(item.get("id")): item.get("center_name", "") or item.get("name", "")
        for item in data
    }


@admin.register(CargoOrder)
class CargoOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "origin_station_name",
        "destination_station_name",
        "status",
        "shipping_fare_status",
        "created_at",
    )
    list_filter = ("status", "shipping_fare_status", "created_at")
    search_fields = ("id", "customer__first_name", "customer__last_name", "customer__phone_number")
    readonly_fields = ("created_at", "updated_at", "origin_station_name", "destination_station_name")
    list_select_related = ("customer",)

    def origin_station_name(self, obj):
        if not hasattr(self, "_station_map"):
            self._station_map = _get_station_name_map()
        name = self._station_map.get(str(obj.origin_station))
        return name or obj.origin_station

    origin_station_name.short_description = "Origin Station"

    def destination_station_name(self, obj):
        if not hasattr(self, "_station_map"):
            self._station_map = _get_station_name_map()
        name = self._station_map.get(str(obj.destination_station))
        return name or obj.destination_station

    destination_station_name.short_description = "Destination Station"
