import uuid

from django.db import models


class Driver(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "auths.User", on_delete=models.CASCADE, related_name="driver"
    )
    vehicle_type = models.ForeignKey(
        "vehicles.VehicleType", on_delete=models.PROTECT, related_name="drivers"
    )
    license_plate = models.CharField(max_length=20)
    national_id_number = models.CharField(max_length=50, blank=True)
    is_verified = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    current_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    current_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    last_location_at = models.DateTimeField(null=True, blank=True)
    rating_avg = models.DecimalField(
        max_digits=3, decimal_places=2, default=5.00
    )
    rating_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["is_online", "vehicle_type"],
                name="idx_drivers_online_vehicle",
            ),
        ]

    def __str__(self):
        return f"Driver {self.user.first_name} {self.user.last_name} — {self.license_plate}"
