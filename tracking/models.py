from django.db import models


class DriverLocationHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    driver = models.ForeignKey(
        "drivers.Driver", on_delete=models.CASCADE, related_name="location_history"
    )
    trip = models.ForeignKey(
        "trips.CargoTrip",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location_history",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["trip", "recorded_at"],
                name="idx_location_history_trip",
            ),
        ]

    def __str__(self):
        return f"Ping {self.id} — driver {self.driver_id}"
