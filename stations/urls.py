from django.urls import path

from .views import CargoStationDetailView, CargoStationListView

urlpatterns = [
    path("", CargoStationListView.as_view(), name="cargo-center-list"),
    path("<uuid:pk>/", CargoStationDetailView.as_view(), name="cargo-center-detail"),
]
