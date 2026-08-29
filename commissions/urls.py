from django.urls import path

from .views import (
    DriverCommissionBandDetailView,
    DriverCommissionBandListCreateView,
    DriverCommissionEstimateView,
)

urlpatterns = [
    path("", DriverCommissionBandListCreateView.as_view(), name="commission-band-list"),
    path("<int:pk>/", DriverCommissionBandDetailView.as_view(), name="commission-band-detail"),
    path("estimate/", DriverCommissionEstimateView.as_view(), name="commission-estimate"),
]