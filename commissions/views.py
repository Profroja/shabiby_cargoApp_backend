from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DriverCommissionBand, get_driver_commission
from .serializers import DriverCommissionBandSerializer


def _require_admin(request):
    return request.user.role == "admin"


class DriverCommissionBandListCreateView(generics.ListCreateAPIView):
    queryset = DriverCommissionBand.objects.all()
    serializer_class = DriverCommissionBandSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        if not _require_admin(request):
            return Response(
                {"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not _require_admin(request):
            return Response(
                {"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)


class DriverCommissionBandDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DriverCommissionBand.objects.all()
    serializer_class = DriverCommissionBandSerializer
    permission_classes = [IsAuthenticated]

    def _require_admin(self, request):
        if not _require_admin(request):
            return self.permission_denied(
                request, message="Admin access required.", code="forbidden"
            )

    def retrieve(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().destroy(request, *args, **kwargs)


class DriverCommissionEstimateView(APIView):
    """POST {distance_km, fare_amount} -> {commission_percent, commission_amount}.

    Lets the driver app preview the commission for a trip before accepting it.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        distance_km = request.data.get("distance_km")
        fare_amount = request.data.get("fare_amount")
        percent, amount = get_driver_commission(distance_km, fare_amount)
        return Response(
            {
                "distance_km": distance_km,
                "fare_amount": fare_amount,
                "commission_percent": str(percent) if percent is not None else None,
                "commission_amount": str(amount) if amount is not None else None,
            }
        )