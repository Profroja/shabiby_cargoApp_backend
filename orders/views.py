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
