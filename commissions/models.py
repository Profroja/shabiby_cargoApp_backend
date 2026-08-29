from decimal import Decimal

from django.db import models


class DriverCommissionBand(models.Model):
    """Commission percentage paid to the driver for a pickup trip's fare,
    selected by the trip's distance (km)."""

    min_distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    max_distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Leave empty to mean 'above min_distance_km'.",
    )
    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage of the pickup fare paid to the driver.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["min_distance_km", "max_distance_km"]

    def __str__(self):
        upper = self.max_distance_km if self.max_distance_km is not None else "∞"
        return f"{self.min_distance_km}–{upper} km → {self.commission_percent}%"


def get_driver_commission(distance_km, fare_amount):
    """Return (commission_percent, commission_amount) for a pickup trip.

    The percentage comes from the first active distance band that contains
    `distance_km`. The amount is `fare_amount * percent / 100`, rounded to
    two decimal places. Returns (None, None) when nothing matches or the
    inputs are missing.
    """
    if distance_km is None or fare_amount is None:
        return None, None

    try:
        distance = Decimal(str(distance_km))
    except (ValueError, TypeError):
        return None, None

    band = (
        DriverCommissionBand.objects.filter(
            is_active=True,
            min_distance_km__lte=distance,
        )
        .filter(
            models.Q(max_distance_km__gte=distance)
            | models.Q(max_distance_km__isnull=True)
        )
        .order_by("min_distance_km")
        .first()
    )
    if band is None:
        return None, None

    try:
        fare = Decimal(str(fare_amount))
    except (ValueError, TypeError):
        return None, None

    amount = (fare * band.commission_percent / Decimal("100")).quantize(Decimal("0.01"))
    return band.commission_percent, amount