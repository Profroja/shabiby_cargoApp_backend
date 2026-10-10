import logging
import time

import requests
from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

EXTERNAL_API_BASE = "https://shabibycargo.co.tz/api"
EXTERNAL_API_USER = getattr(settings, "EXTERNAL_API_USER", "cargoadmin")
EXTERNAL_API_PASS = getattr(settings, "EXTERNAL_API_PASS", "cargoadmin12345?")

_cached_token = None

# The main system's station list barely changes, but drivers' phones poll the
# request list every few seconds; keep it for a few minutes per process.
EXTERNAL_CACHE_SECONDS = 300
_external_cache = {}


def _get_external_token():
    global _cached_token
    try:
        resp = requests.post(
            f"{EXTERNAL_API_BASE}/token/",
            json={"username": EXTERNAL_API_USER, "password": EXTERNAL_API_PASS},
            timeout=10,
        )
        if resp.status_code == 200:
            _cached_token = resp.json().get("access")
            return _cached_token
    except Exception as e:
        logger.error(f"External API login failed: {e}")
    return None


def _fetch_external_centers(active_only=True):
    """Stations from the main Shabiby system (shabibycargo.co.tz), cached briefly."""
    cached = _external_cache.get(active_only)
    if cached and time.monotonic() - cached[0] < EXTERNAL_CACHE_SECONDS:
        return cached[1]
    data = _fetch_external_centers_uncached(active_only)
    if data is not None:
        _external_cache[active_only] = (time.monotonic(), data)
    return data


def _fetch_external_centers_uncached(active_only):
    token = _cached_token or _get_external_token()
    if not token:
        return None

    # Try /stations/ first (has latitude/longitude), fall back to /cargo-centers/
    for endpoint in ["/stations/", "/cargo-centers/"]:
        url = f"{EXTERNAL_API_BASE}{endpoint}"
        if not active_only:
            url += "?active_only=false"

        try:
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 401:
                token = _get_external_token()
                if not token:
                    return None
                resp = requests.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"External API fetch from {endpoint} failed: {e}")
            continue
    return None


def _external_get(path, token):
    resp = requests.get(f"{EXTERNAL_API_BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    return resp.json() if resp.status_code == 200 else None


def fetch_external_for_import():
    """All main-system cargo centers, with coordinates where the main system has them.
    Returns a list of station dicts, or None if the main system can't be reached."""
    token = _get_external_token()
    if not token:
        return None
    try:
        centers = _external_get("/cargo-centers/?active_only=false", token)
        located = _external_get("/stations/?active_only=false", token) or []
    except Exception as e:
        logger.error(f"External import fetch failed: {e}")
        return None
    if centers is None:
        return None
    coords = {
        (item.get("center_name") or "").strip().lower(): (item.get("latitude"), item.get("longitude"))
        for item in located
    }
    for item in centers:
        if item.get("latitude") is None or item.get("longitude") is None:
            name = (item.get("center_name") or "").strip().lower()
            item["latitude"], item["longitude"] = coords.get(name, (None, None))
    return centers


def station_record(station):
    """A local CargoStation in the same shape the main system's API uses."""
    location = ", ".join(p for p in [station.city, station.region] if p) or station.address
    return {
        "id": str(station.id),
        "center_name": station.name,
        "name": station.name,
        "location": location,
        "branch_code": station.branch_code,
        "is_active": station.is_active,
        "latitude": float(station.latitude) if station.latitude is not None else None,
        "longitude": float(station.longitude) if station.longitude is not None else None,
        "price_per_km": float(station.price_per_km) if station.price_per_km is not None else None,
        "min_fare": float(station.min_fare) if station.min_fare is not None else None,
        "created_at": station.created_at.isoformat() if station.created_at else None,
        "updated_at": station.updated_at.isoformat() if station.updated_at else None,
    }


def _local_stations(active_only=True):
    from .models import CargoStation

    qs = CargoStation.objects.all().order_by("name")
    if active_only:
        qs = qs.filter(is_active=True)
    return [station_record(s) for s in qs]


def _fetch_cargo_centers(active_only=True):
    """Every station the backend knows about, for looking stations up by ID.

    Admin-managed stations (local CargoStation) come first. Main-system stations
    are appended so orders created before the switch still resolve their names.
    """
    local = _local_stations(active_only)
    external = _fetch_external_centers(active_only) or []
    if not local:
        return external or None
    local_ids = {r["id"] for r in local}
    return local + [item for item in external if str(item.get("id")) not in local_ids]


def _app_station_list(active_only=True):
    """Stations customers can choose: the admin-managed list once it has any
    stations, otherwise the main system's list (so nothing breaks before setup)."""
    from .models import CargoStation

    if CargoStation.objects.exists():
        return _local_stations(active_only)
    return _fetch_external_centers(active_only)


def _get_center_map():
    """Return a dict mapping station ID (str) -> station data (local + main system)."""
    data = _fetch_cargo_centers(active_only=False)
    if not data:
        return {}
    return {str(item.get("id")): item for item in data}


class CargoCenterListView(generics.GenericAPIView):
    def get(self, request):
        active_only = request.query_params.get("active_only", "true")
        active = active_only.lower() != "false"

        data = _app_station_list(active_only=active)
        if data is None:
            return Response(
                {"error": "Failed to fetch cargo centers from external service."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        results = []
        for item in data:
            if active and not item.get("is_active", True):
                continue
            results.append({
                "id": item.get("id"),
                "name": item.get("center_name", ""),
                "center_name": item.get("center_name", ""),
                "location": item.get("location", ""),
                "branch_code": item.get("branch_code", ""),
                "is_active": item.get("is_active", True),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "price_per_km": item.get("price_per_km"),
                "min_fare": item.get("min_fare"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })
        return Response(results)


class CargoCenterDetailView(generics.GenericAPIView):
    def get(self, request, pk):
        data = _fetch_cargo_centers(active_only=False)
        if data is None:
            return Response(
                {"error": "Failed to fetch cargo center from external service."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        for item in data:
            if str(item.get("id")) == str(pk):
                return Response({
                    "id": item.get("id"),
                    "name": item.get("center_name", ""),
                    "center_name": item.get("center_name", ""),
                    "location": item.get("location", ""),
                    "branch_code": item.get("branch_code", ""),
                    "is_active": item.get("is_active", True),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "price_per_km": item.get("price_per_km"),
                    "min_fare": item.get("min_fare"),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                })
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
