from rest_framework import generics

from .models import CargoSize
from .serializers import CargoSizeSerializer


class CargoSizeListView(generics.ListCreateAPIView):
    queryset = CargoSize.objects.filter(is_active=True)
    serializer_class = CargoSizeSerializer


class CargoSizeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CargoSize.objects.all()
    serializer_class = CargoSizeSerializer
