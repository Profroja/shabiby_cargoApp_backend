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
        # Recalculate driver's average rating
        from django.db.models import Avg, Count
        agg = DriverRating.objects.filter(driver=self.driver).aggregate(
            avg=Avg("stars"), count=Count("id")
        )
        self.driver.rating_avg = round(agg["avg"] or 5.0, 2)
        self.driver.rating_count = agg["count"] or 0
        self.driver.save(update_fields=["rating_avg", "rating_count"])
