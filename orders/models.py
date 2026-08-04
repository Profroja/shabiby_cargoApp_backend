import uuid

from django.db import models


class CargoOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        PICKUP_IN_PROGRESS = "pickup_in_progress", "Pickup In Progress"
        AT_ORIGIN_STATION = "at_origin_station", "At Origin Station"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        "auths.User", on_delete=models.CASCADE, related_name="orders"
    )
    origin_station = models.CharField(max_length=50)
    destination_station = models.CharField(max_length=50)
    cargo_size = models.IntegerField(default=1)
    estimated_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    description = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    receiver_name = models.CharField(max_length=150, blank=True, default="")
    receiver_phone = models.CharField(max_length=20, blank=True, default="")
    receiver_address = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.SUBMITTED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer"], name="idx_orders_customer"),
            models.Index(fields=["status"], name="idx_orders_status"),
        ]

    def __str__(self):
        return f"Order {self.id} — {self.status}"
