from django.contrib import admin

from .models import DriverCommissionBand


@admin.register(DriverCommissionBand)
class DriverCommissionBandAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "min_distance_km",
        "max_distance_km",
        "commission_percent",
        "is_active",
        "created_at",
    )
    list_editable = ("is_active",)
    list_filter = ("is_active",)
    ordering = ("min_distance_km",)