from django.urls import path

from .views import FareEstimateView, FareRateListView

urlpatterns = [
    path("", FareRateListView.as_view(), name="fare-rate-list"),
    path("estimate/", FareEstimateView.as_view(), name="fare-estimate"),
]
