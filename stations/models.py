import uuid

from django.db import models


class CargoStation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    branch_code = models.CharField(max_length=10, unique=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    zone = models.ForeignKey(
        "farezones.FareZone", on_delete=models.PROTECT,
        related_name="stations", null=True, blank=True,
    )
    # Pickup fare for trips to this station: distance x price_per_km x vehicle
    # multiplier, never below min_fare. Empty = settings.DEFAULT_PRICE_PER_KM / no minimum.
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["zone"], name="idx_stations_zone"),
        ]

    def __str__(self):
        return self.name


class StationFareBand(models.Model):
    """Pickup fare for trips to a station within a distance range, e.g. 0–3 km = 2,000.
    When a station has bands they set the fare; otherwise its price per km does."""

    id = models.BigAutoField(primary_key=True)
    station = models.ForeignKey(CargoStation, on_delete=models.CASCADE, related_name="fare_bands")
    min_km = models.DecimalField(max_digits=8, decimal_places=2)
    max_km = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="Empty = and above."
    )
    fare = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["min_km"]

    def covers(self, km):
        return self.min_km <= km and (self.max_km is None or km < self.max_km)

    def __str__(self):
        return f"{self.station_id}: {self.min_km}–{self.max_km or '…'} km = {self.fare}"
