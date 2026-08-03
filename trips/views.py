from rest_framework import generics

from .models import CargoTrip
from .serializers import CargoTripSerializer


class CargoTripListView(generics.ListCreateAPIView):
    serializer_class = CargoTripSerializer

    def get_queryset(self):
        return CargoTrip.objects.filter(order__customer=self.request.user)


class CargoTripDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CargoTripSerializer

    def get_queryset(self):
        return CargoTrip.objects.filter(order__customer=self.request.user)
