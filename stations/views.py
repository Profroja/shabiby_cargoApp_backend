import logging

import requests
from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

EXTERNAL_API_BASE = "https://shabibycargo.co.tz/api"
EXTERNAL_API_USER = getattr(settings, "EXTERNAL_API_USER", "cargoadmin")
EXTERNAL_API_PASS = getattr(settings, "EXTERNAL_API_PASS", "cargoadmin12345?")

_cached_token = None


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


def _fetch_cargo_centers(active_only=True):
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


def _get_center_map():
    """Return a dict mapping station ID (str) -> raw station data from external API."""
    data = _fetch_cargo_centers(active_only=False)
    if not data:
        return {}
    return {str(item.get("id")): item for item in data}


class CargoCenterListView(generics.GenericAPIView):
    def get(self, request):
        active_only = request.query_params.get("active_only", "true")
        active = active_only.lower() != "false"

        data = _fetch_cargo_centers(active_only=active)
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
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                })
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
