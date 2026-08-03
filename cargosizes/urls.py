from django.urls import path

from .views import CargoSizeDetailView, CargoSizeListView

urlpatterns = [
    path("", CargoSizeListView.as_view(), name="cargo-size-list"),
    path("<int:pk>/", CargoSizeDetailView.as_view(), name="cargo-size-detail"),
]
