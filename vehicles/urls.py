from django.urls import path

from .views import VehicleTypeDetailView, VehicleTypeListView

urlpatterns = [
    path("", VehicleTypeListView.as_view(), name="vehicle-type-list"),
    path("<int:pk>/", VehicleTypeDetailView.as_view(), name="vehicle-type-detail"),
]
