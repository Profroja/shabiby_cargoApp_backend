from django.urls import path

from .views import CargoOrderDetailView, CargoOrderListView

urlpatterns = [
    path("", CargoOrderListView.as_view(), name="cargo-order-list"),
    path("<uuid:pk>/", CargoOrderDetailView.as_view(), name="cargo-order-detail"),
]
