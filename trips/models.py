import uuid

from django.db import models


class CargoTrip(models.Model):
    class LegType(models.TextChoices):
        PICKUP = "pickup", "Pickup"
        STATION_TRANSFER = "station_transfer", "Station Transfer"
        FINAL_DELIVERY = "final_delivery", "Final Delivery"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        SEARCHING_DRIVER = "searching_driver", "Searching Driver"
        DRIVER_ASSIGNED = "driver_assigned", "Driver Assigned"
        EN_ROUTE_TO_PICKUP = "en_route_to_pickup", "En Route To Pickup"
        ARRIVED_AT_PICKUP = "arrived_at_pickup", "Arrived At Pickup"
        PICKED_UP = "picked_up", "Picked Up"
        DELIVERED_TO_STATION = "delivered_to_station", "Delivered To Station"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.CargoOrder", on_delete=models.CASCADE, related_name="trips"
    )
    leg_type = models.CharField(
        max_length=20, choices=LegType.choices, default=LegType.PICKUP
    )
    driver = models.ForeignKey(
        "drivers.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trips",
    )
    vehicle_type = models.IntegerField(default=1)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_address_text = models.TextField(blank=True, default="")
    destination_station = models.CharField(max_length=50)
    distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    fare_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.REQUESTED
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    driver_assigned_at = models.DateTimeField(null=True, blank=True)
    arrived_at_pickup_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["order"], name="idx_trips_order"),
            models.Index(fields=["driver"], name="idx_trips_driver"),
            models.Index(fields=["status"], name="idx_trips_status"),
        ]

    def __str__(self):
        return f"Trip {self.id} — {self.leg_type} / {self.status}"
