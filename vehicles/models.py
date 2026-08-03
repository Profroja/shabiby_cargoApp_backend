from django.db import models


class VehicleType(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=50)
    max_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.display_name
