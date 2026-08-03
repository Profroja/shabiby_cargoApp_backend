from django.db import models


class FareRate(models.Model):
    id = models.AutoField(primary_key=True)
    zone = models.ForeignKey(
        "farezones.FareZone", on_delete=models.PROTECT, related_name="rates"
    )
    vehicle_type = models.ForeignKey(
        "vehicles.VehicleType", on_delete=models.PROTECT, related_name="rates"
    )
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    rate_per_km = models.DecimalField(max_digits=10, decimal_places=2)
    min_fare = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="TZS")
    effective_from = models.DateTimeField(auto_now_add=True)
    effective_to = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["zone", "vehicle_type"],
                condition=models.Q(effective_to__isnull=True),
                name="one_active_rate_zone_vehicle",
            ),
        ]

    def __str__(self):
        return f"{self.zone} / {self.vehicle_type} — {self.currency}"
