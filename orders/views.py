from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CargoOrder
from .serializers import CargoOrderSerializer


class CargoOrderListView(generics.ListCreateAPIView):
    serializer_class = CargoOrderSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return CargoOrder.objects.filter(customer=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        order = serializer.save(customer=self.request.user, status=CargoOrder.Status.SUBMITTED)


class CargoOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CargoOrderSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return CargoOrder.objects.filter(customer=self.request.user)

    def perform_destroy(self, instance):
        """Customer cancels. Before a driver accepts, the order is removed; after that it
        is kept and marked cancelled, so the driver sees the cancellation and the trip
        stays on record."""
        from django.utils import timezone

        from trips.models import CargoTrip

        if not instance.trips.filter(driver__isnull=False).exists():
            instance.delete()
            return
        now = timezone.now()
        instance.trips.exclude(status__in=["delivered_to_station", "cancelled"]).update(
            status=CargoTrip.Status.CANCELLED, cancelled_at=now, updated_at=now
        )
        instance.status = CargoOrder.Status.CANCELLED
        instance.save(update_fields=["status", "updated_at"])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_shipping_fare(request, pk):
    """Admin sets the shipping fare for an order after reviewing the cargo photo."""
    if request.user.role != "admin":
        return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        order = CargoOrder.objects.get(pk=pk)
    except CargoOrder.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    fare = request.data.get("shipping_fare")
    if fare is None:
        return Response({"error": "shipping_fare is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        fare = str(fare)
        from decimal import Decimal, InvalidOperation
        order.shipping_fare = Decimal(fare)
    except (InvalidOperation, ValueError):
        return Response({"error": "Invalid fare amount."}, status=status.HTTP_400_BAD_REQUEST)

    order.shipping_fare_status = CargoOrder.ShippingFareStatus.PRICED
    order.save(update_fields=["shipping_fare", "shipping_fare_status", "updated_at"])

    serializer = CargoOrderSerializer(order, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_order_status(request, pk):
    """Station staff move an order between stations.
    Body: {"status": "in_transit" | "arrived_at_destination" | "delivered"}"""
    if request.user.role not in ("admin", "agent"):
        return Response({"error": "Station staff access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        order = CargoOrder.objects.get(pk=pk)
    except CargoOrder.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.user.role == "agent":
        station_id = str(request.user.station_id or "")
        if not station_id or station_id not in (str(order.origin_station), str(order.destination_station)):
            return Response({"error": "This order is not for your station."}, status=status.HTTP_403_FORBIDDEN)

    error = order.advance_station_status(request.data.get("status"))
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    serializer = CargoOrderSerializer(order, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def claim_paid(request, pk):
    """Customer says they paid the shipping fare by Lipa Namba. Body: {"reference": "<code>"} (optional)."""
    from django.utils import timezone

    try:
        order = CargoOrder.objects.get(pk=pk, customer=request.user)
    except CargoOrder.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    if order.shipping_fare_status == CargoOrder.ShippingFareStatus.PAID:
        return Response({"error": "This order is already paid."}, status=status.HTTP_400_BAD_REQUEST)
    if order.shipping_fare is None or order.shipping_fare_status == CargoOrder.ShippingFareStatus.PENDING:
        return Response({"error": "The shipping fare hasn't been set yet."}, status=status.HTTP_400_BAD_REQUEST)

    order.payment_reference = str(request.data.get("reference", "")).strip()[:100]
    order.payment_claimed_at = timezone.now()
    order.shipping_fare_status = CargoOrder.ShippingFareStatus.AWAITING_CONFIRMATION
    order.save(update_fields=["payment_reference", "payment_claimed_at", "shipping_fare_status", "updated_at"])
    return Response(CargoOrderSerializer(order, context={"request": request}).data, status=status.HTTP_200_OK)
