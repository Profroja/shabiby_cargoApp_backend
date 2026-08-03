from decimal import Decimal

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from stations.models import CargoStation

from .models import FareRate
from .serializers import FareRateSerializer


class FareRateListView(generics.ListCreateAPIView):
    queryset = FareRate.objects.filter(effective_to__isnull=True)
    serializer_class = FareRateSerializer


class FareEstimateView(APIView):
    """
    POST /api/fare-estimate/
    {
        "station_id": "<uuid>",
        "distance_km": 5.2
    }
    Returns fare for each active vehicle type in that station's zone.
    """

    def post(self, request):
        station_id = request.data.get("station_id")
        distance_km = request.data.get("distance_km")

        if not station_id or distance_km is None:
            return Response(
                {"error": "station_id and distance_km are required."},
                status=400,
            )

        try:
            station = CargoStation.objects.get(id=station_id)
        except CargoStation.DoesNotExist:
            return Response({"error": "Station not found."}, status=404)

        if not station.zone_id:
            return Response(
                {"error": "Station has no fare zone assigned."},
                status=400,
            )

        distance = Decimal(str(distance_km))
        rates = FareRate.objects.filter(
            zone_id=station.zone_id,
            effective_to__isnull=True,
            vehicle_type__is_active=True,
        ).select_related("vehicle_type")

        results = []
        for rate in rates:
            fare = max(rate.min_fare, rate.base_fare + rate.rate_per_km * distance)
            results.append(
                {
                    "vehicle_type_id": rate.vehicle_type_id,
                    "vehicle_type_name": rate.vehicle_type.name,
                    "vehicle_type_display": rate.vehicle_type.display_name,
                    "fare": str(fare.quantize(Decimal("0.01"))),
                    "currency": rate.currency,
                    "rate_id": rate.id,
                }
            )

        return Response(
            {
                "station": str(station.id),
                "station_name": station.name,
                "distance_km": str(distance),
                "estimates": results,
            }
        )
