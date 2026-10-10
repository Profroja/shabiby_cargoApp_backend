"""A driver's account with the company: subscription periods, payments made to
the company, and feedback recorded by admins."""
import uuid

from django.db import models


class DriverSubscription(models.Model):
    """One subscription period. Drivers usually start on a free period, then move
    to paid ones. A driver can only accept trips while a period covers today,
    unless they have never been given any period (older drivers keep working)."""

    class Plan(models.TextChoices):
        FREE = "free", "Free"
        PAID = "paid", "Paid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey("drivers.Driver", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True, help_text="Empty = no end date.")
    fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="What the driver owes for this period (0 for free periods).",
    )
    note = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "auths.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-starts_on", "-created_at"]
        indexes = [models.Index(fields=["driver", "starts_on"], name="idx_sub_driver_start")]

    def covers(self, day):
        return self.starts_on <= day and (self.ends_on is None or self.ends_on >= day)

    def __str__(self):
        return f"{self.get_plan_display()} {self.starts_on}–{self.ends_on or '…'} for {self.driver_id}"


class DriverPayment(models.Model):
    """Money a driver paid to the company."""

    class Kind(models.TextChoices):
        COMMISSION = "commission", "Trip commission"
        SUBSCRIPTION = "subscription", "Subscription"

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile money"
        BANK = "bank", "Bank"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey("drivers.Driver", on_delete=models.CASCADE, related_name="payments")
    kind = models.CharField(max_length=15, choices=Kind.choices, default=Kind.COMMISSION)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=15, choices=Method.choices, default=Method.CASH)
    reference = models.CharField(max_length=100, blank=True, default="", help_text="e.g. M-Pesa code")
    note = models.TextField(blank=True, default="")
    paid_on = models.DateField()
    recorded_by = models.ForeignKey(
        "auths.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_on", "-created_at"]
        indexes = [models.Index(fields=["driver", "paid_on"], name="idx_payment_driver_date")]

    def __str__(self):
        return f"{self.amount} {self.kind} from {self.driver_id} on {self.paid_on}"


class DriverFeedback(models.Model):
    """Good/bad feedback or an issue recorded by an admin. Stars, when given,
    count toward the driver's rating alongside customer ratings."""

    class Category(models.TextChoices):
        GOOD = "good", "Good"
        BAD = "bad", "Bad"
        ISSUE = "issue", "Issue"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey("drivers.Driver", on_delete=models.CASCADE, related_name="feedback")
    trip = models.ForeignKey(
        "trips.CargoTrip", on_delete=models.SET_NULL, null=True, blank=True, related_name="feedback"
    )
    category = models.CharField(max_length=10, choices=Category.choices)
    stars = models.PositiveSmallIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True, default="")
    is_resolved = models.BooleanField(default=False, help_text="Issues only: resolved issues stop holding the level back.")
    recorded_by = models.ForeignKey(
        "auths.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["driver", "category"], name="idx_feedback_driver_cat")]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .performance import recalc_rating

        recalc_rating(self.driver)

    def delete(self, *args, **kwargs):
        driver = self.driver
        result = super().delete(*args, **kwargs)
        from .performance import recalc_rating

        recalc_rating(driver)
        return result

    def __str__(self):
        return f"{self.get_category_display()} feedback for {self.driver_id}"
