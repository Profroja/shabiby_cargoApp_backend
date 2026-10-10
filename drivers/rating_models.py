import uuid

from django.db import models


class DriverRating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(
        "drivers.Driver", on_delete=models.CASCADE, related_name="ratings"
    )
    trip = models.ForeignKey(
        "trips.CargoTrip", on_delete=models.CASCADE, related_name="ratings"
    )
    customer = models.ForeignKey(
        "auths.User", on_delete=models.CASCADE, related_name="given_ratings"
    )
    stars = models.IntegerField()
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("trip", "customer")
        indexes = [
            models.Index(fields=["driver"], name="idx_rating_driver"),
        ]

    def __str__(self):
        return f"Rating {self.stars}★ for {self.driver} on trip {self.trip_id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .performance import recalc_rating

        recalc_rating(self.driver)
