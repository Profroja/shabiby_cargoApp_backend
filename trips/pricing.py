"""Pickup fares, priced on the server from the destination station's rate."""
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError

# Vehicle type id -> fare multiplier. Must match the vehicle list in the
# customer app (src/components/request/FareStep.tsx): Boda, Guta, Small van.
VEHICLE_FARE_MULTIPLIERS = {1: Decimal("1"), 2: Decimal("2"), 3: Decimal("3")}


def station_rates(station_id):
    """(price_per_km, min_fare) for a cargo station; defaults when unset or unknown."""
    from stations.models import CargoStation

    try:
        station = CargoStation.objects.filter(pk=station_id).first()
    except (ValidationError, ValueError):  # ids from the old main-system station list
        station = None
    default_price = Decimal(str(getattr(settings, "DEFAULT_PRICE_PER_KM", 600)))
    price = station.price_per_km if station and station.price_per_km is not None else default_price
    min_fare = station.min_fare if station and station.min_fare is not None else Decimal("0")
    return price, min_fare


def pickup_fare(station_id, distance_km, vehicle_type):
    """distance (at least 1 km) x station price per km x vehicle multiplier, whole TZS."""
    price, min_fare = station_rates(station_id)
    distance = max(Decimal(str(distance_km or 0)), Decimal("1"))
    multiplier = VEHICLE_FARE_MULTIPLIERS.get(int(vehicle_type or 1), Decimal("1"))
    fare = (distance * price * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(fare, min_fare)
