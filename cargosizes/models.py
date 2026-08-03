from django.db import models


class CargoSize(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=30, unique=True)
    max_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
