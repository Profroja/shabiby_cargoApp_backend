from rest_framework import generics

from .models import VehicleType
from .serializers import VehicleTypeSerializer


class VehicleTypeListView(generics.ListCreateAPIView):
    queryset = VehicleType.objects.filter(is_active=True)
    serializer_class = VehicleTypeSerializer


class VehicleTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VehicleType.objects.all()
    serializer_class = VehicleTypeSerializer
