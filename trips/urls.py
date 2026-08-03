from django.urls import path

from .views import CargoTripDetailView, CargoTripListView

urlpatterns = [
    path("", CargoTripListView.as_view(), name="cargo-trip-list"),
    path("<uuid:pk>/", CargoTripDetailView.as_view(), name="cargo-trip-detail"),
]
