from django.urls import path

from .views import CargoOrderDetailView, CargoOrderListView, set_shipping_fare

urlpatterns = [
    path("", CargoOrderListView.as_view(), name="cargo-order-list"),
    path("<uuid:pk>/", CargoOrderDetailView.as_view(), name="cargo-order-detail"),
    path("<uuid:pk>/set-shipping-fare/", set_shipping_fare, name="set-shipping-fare"),
]
