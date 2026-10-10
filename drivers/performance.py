"""Driver standing: rating, level, subscription and money owed to the company."""
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from commissions.models import get_driver_commission

ZERO = Decimal("0")

# Levels a driver climbs with completed trips and a good rating. Unresolved
# issues hold a driver back: a level allows at most `max_open_issues`.
LEVELS = [
    {"level": 1, "name": "New", "min_trips": 0, "min_rating": 0.0, "max_open_issues": None, "color": "#6c757d"},
    {"level": 2, "name": "Bronze", "min_trips": 10, "min_rating": 3.5, "max_open_issues": 2, "color": "#a0522d"},
    {"level": 3, "name": "Silver", "min_trips": 50, "min_rating": 4.0, "max_open_issues": 1, "color": "#708090"},
    {"level": 4, "name": "Gold", "min_trips": 150, "min_rating": 4.5, "max_open_issues": 0, "color": "#c9a227"},
    {"level": 5, "name": "Platinum", "min_trips": 300, "min_rating": 4.8, "max_open_issues": 0, "color": "#5b6dc8"},
]


def _qualifies(tier, trips, rating, open_issues):
    return (
        trips >= tier["min_trips"]
        and rating >= tier["min_rating"]
        and (tier["max_open_issues"] is None or open_issues <= tier["max_open_issues"])
    )


def driver_level(trips, rating, open_issues):
    """Current level plus what is still needed for the next one."""
    rating = float(rating)
    current = LEVELS[0]
    for tier in LEVELS:
        if _qualifies(tier, trips, rating, open_issues):
            current = tier
    following = next((t for t in LEVELS if t["level"] == current["level"] + 1), None)
    needs = []
    if following:
        if trips < following["min_trips"]:
            needs.append(f"{following['min_trips'] - trips} more completed trips")
        if rating < following["min_rating"]:
            needs.append(f"rating of {following['min_rating']}+")
        if following["max_open_issues"] is not None and open_issues > following["max_open_issues"]:
            needs.append(f"resolve {open_issues - following['max_open_issues']} open issue(s)")
    return {**current, "next": following, "needs": needs}


def recalc_rating(driver):
    """Average of customer ratings and admin feedback that carries stars."""
    from .account_models import DriverFeedback
    from .rating_models import DriverRating

    stars = list(DriverRating.objects.filter(driver=driver).values_list("stars", flat=True))
    stars += list(
        DriverFeedback.objects.filter(driver=driver, stars__isnull=False).values_list("stars", flat=True)
    )
    driver.rating_avg = Decimal(str(round(sum(stars) / len(stars), 2))) if stars else Decimal("5.00")
    driver.rating_count = len(stars)
    driver.save(update_fields=["rating_avg", "rating_count", "updated_at"])


def trip_split(trip):
    """(fare, driver_earning, company_share). Values saved at delivery win; otherwise
    computed from the commission bands (driver's share), falling back to
    settings.DEFAULT_DRIVER_SHARE_PERCENT when no band matches."""
    fare = trip.fare_amount or ZERO
    if trip.driver_earning is not None and trip.company_share is not None:
        return fare, trip.driver_earning, trip.company_share
    _percent, earning = get_driver_commission(trip.distance_km, trip.fare_amount)
    if earning is None:
        share = Decimal(str(getattr(settings, "DEFAULT_DRIVER_SHARE_PERCENT", 85)))
        earning = (fare * share / Decimal("100")).quantize(Decimal("0.01"))
    return fare, earning, fare - earning


def subscription_status(periods, today=None):
    """('none' | 'free' | 'paid' | 'expired', current period or None).
    'none' means the driver was never given a period; they may still work."""
    today = today or timezone.localdate()
    started = [p for p in periods if p.starts_on <= today]
    current = next((p for p in sorted(started, key=lambda p: p.starts_on, reverse=True) if p.covers(today)), None)
    if current:
        return current.plan, current
    if started:
        return "expired", None
    return "none", None


def can_accept_trips(driver):
    status, _ = subscription_status(list(driver.subscriptions.all()))
    return status != "expired"


def _account(driver, trips, payments, periods, feedback, today):
    completed = [t for t in trips if t.status == "delivered_to_station"]
    fares = earnings = company = shipping = ZERO
    for trip in completed:
        fare, earning, share = trip_split(trip)
        fares += fare
        earnings += earning
        company += share
        # The driver also collects the shipping fare, all of which belongs to the company.
        shipping += trip.order.shipping_fare or ZERO

    commission_paid = sum((p.amount for p in payments if p.kind == "commission"), ZERO)
    subscription_paid = sum((p.amount for p in payments if p.kind == "subscription"), ZERO)
    subscription_fees = sum((p.fee for p in periods if p.plan == "paid" and p.starts_on <= today), ZERO)

    status, current = subscription_status(periods, today)
    open_issues = sum(1 for f in feedback if f.category == "issue" and not f.is_resolved)
    level = driver_level(len(completed), driver.rating_avg, open_issues)

    commission_due = company + shipping - commission_paid
    subscription_due = subscription_fees - subscription_paid
    return {
        "completed_trips": len(completed),
        "fares_total": fares,
        "earnings_total": earnings,
        "company_total": company + shipping,
        "pickup_company_total": company,
        "shipping_total": shipping,
        "commission_paid": commission_paid,
        "commission_due": commission_due,
        "subscription_fees": subscription_fees,
        "subscription_paid": subscription_paid,
        "subscription_due": subscription_due,
        "balance_due": commission_due + subscription_due,
        "paid_total": commission_paid + subscription_paid,
        "subscription_status": status,
        "subscription": current,
        "subscription_days_left": (current.ends_on - today).days if current and current.ends_on else None,
        "open_issues": open_issues,
        "level": level,
    }


def driver_account(driver):
    """Everything the admin panel and the driver app show about one driver."""
    today = timezone.localdate()
    return _account(
        driver,
        list(driver.trips.select_related("order")),
        list(driver.payments.all()),
        list(driver.subscriptions.all()),
        list(driver.feedback.all()),
        today,
    )


def accounts_for(drivers):
    """driver.id -> account for many drivers, with a fixed number of queries."""
    from trips.models import CargoTrip

    from .account_models import DriverFeedback, DriverPayment, DriverSubscription

    drivers = list(drivers)
    ids = [d.id for d in drivers]
    grouped = {name: defaultdict(list) for name in ("trips", "payments", "periods", "feedback")}
    for t in CargoTrip.objects.filter(driver_id__in=ids, status="delivered_to_station").select_related("order"):
        grouped["trips"][t.driver_id].append(t)
    for p in DriverPayment.objects.filter(driver_id__in=ids):
        grouped["payments"][p.driver_id].append(p)
    for s in DriverSubscription.objects.filter(driver_id__in=ids):
        grouped["periods"][s.driver_id].append(s)
    for f in DriverFeedback.objects.filter(driver_id__in=ids, category="issue", is_resolved=False):
        grouped["feedback"][f.driver_id].append(f)

    today = timezone.localdate()
    return {
        d.id: _account(
            d,
            grouped["trips"][d.id],
            grouped["payments"][d.id],
            grouped["periods"][d.id],
            grouped["feedback"][d.id],
            today,
        )
        for d in drivers
    }
