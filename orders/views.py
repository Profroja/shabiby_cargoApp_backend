from rest_framework import generics

from trips.models import CargoTrip

from .models import CargoOrder
from .serializers import CargoOrderSerializer


class CargoOrderListView(generics.ListCreateAPIView):
    serializer_class = CargoOrderSerializer

    def get_queryset(self):
        return CargoOrder.objects.filter(customer=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        order = serializer.save(customer=self.request.user, status=CargoOrder.Status.SUBMITTED)
        # Auto-create a pickup trip in searching_driver state
        CargoTrip.objects.create(
            order=order,
            leg_type=CargoTrip.LegType.PICKUP,
            vehicle_type=1,
            pickup_latitude=0,
            pickup_longitude=0,
            pickup_address_text="",
            destination_station=order.destination_station,
            status=CargoTrip.Status.SEARCHING_DRIVER,
        )


class CargoOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CargoOrderSerializer

    def get_queryset(self):
        return CargoOrder.objects.filter(customer=self.request.user)
