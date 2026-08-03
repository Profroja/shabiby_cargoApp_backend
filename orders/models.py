import uuid

from django.db import models


class CargoOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PICKUP_IN_PROGRESS = "pickup_in_progress", "Pickup In Progress"
        AT_ORIGIN_STATION = "at_origin_station", "At Origin Station"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        "auths.User", on_delete=models.CASCADE, related_name="orders"
    )
    origin_station = models.ForeignKey(
        "stations.CargoStation",
        on_delete=models.PROTECT,
        related_name="orders_as_origin",
    )
    destination_station = models.ForeignKey(
        "stations.CargoStation",
        on_delete=models.PROTECT,
        related_name="orders_as_destination",
    )
    cargo_size = models.ForeignKey(
        "cargosizes.CargoSize", on_delete=models.PROTECT, related_name="orders"
    )
    estimated_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer"], name="idx_orders_customer"),
            models.Index(fields=["status"], name="idx_orders_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(
                    origin_station=models.F("destination_station")
                ),
                name="origin_ne_destination",
            ),
        ]

    def __str__(self):
        return f"Order {self.id} — {self.status}"
