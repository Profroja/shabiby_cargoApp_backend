import uuid

from django.db import models


class Driver(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "auths.User", on_delete=models.CASCADE, related_name="driver"
    )
    vehicle_type = models.ForeignKey(
        "vehicles.VehicleType", on_delete=models.PROTECT, related_name="drivers",
        null=True, blank=True,
    )
    license_plate = models.CharField(max_length=20, blank=True, default="")
    license_number = models.CharField(max_length=50, blank=True, default="")
    national_id_number = models.CharField(max_length=50, blank=True, default="")
    vehicle_name = models.CharField(max_length=100, blank=True, default="")
    vehicle_color = models.CharField(max_length=50, blank=True, default="")
    license_photo = models.ImageField(upload_to="driver_licenses/", null=True, blank=True)
    profile_photo = models.ImageField(upload_to="driver_profiles/", null=True, blank=True)
    approval_status = models.CharField(
        max_length=15, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
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
    region = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["is_online", "vehicle_type"],
                name="idx_drivers_online_vehicle",
            ),
            models.Index(fields=["approval_status"], name="idx_drivers_approval"),
        ]

    def __str__(self):
        return f"Driver {self.user.first_name} {self.user.last_name} — {self.license_plate}"


from .rating_models import DriverRating  # noqa: E402,F401
