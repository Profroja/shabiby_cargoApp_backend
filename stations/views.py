from rest_framework import generics

from .models import CargoStation
from .serializers import CargoStationSerializer


class CargoStationListView(generics.ListCreateAPIView):
    serializer_class = CargoStationSerializer

    def get_queryset(self):
        queryset = CargoStation.objects.all()
        active_only = self.request.query_params.get("active_only", "true")
        if active_only.lower() != "false":
            queryset = queryset.filter(is_active=True)
        return queryset


class CargoStationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CargoStation.objects.all()
    serializer_class = CargoStationSerializer
