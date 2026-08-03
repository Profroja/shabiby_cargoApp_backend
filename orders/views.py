from rest_framework import generics

from .models import CargoOrder
from .serializers import CargoOrderSerializer


class CargoOrderListView(generics.ListCreateAPIView):
    serializer_class = CargoOrderSerializer

    def get_queryset(self):
        return CargoOrder.objects.filter(customer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)


class CargoOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CargoOrderSerializer

    def get_queryset(self):
        return CargoOrder.objects.filter(customer=self.request.user)
