from django.urls import path

from .views import (
    CargoTripDetailView,
    CargoTripListView,
    DriverAvailableTripsView,
    DriverMyTripsView,
    DriverTripHistoryView,
    accept_trip,
    trip_status,
    update_driver_location,
    update_trip_status,
)

urlpatterns = [
    path("", CargoTripListView.as_view(), name="cargo-trip-list"),
    path("<uuid:pk>/", CargoTripDetailView.as_view(), name="cargo-trip-detail"),
    path("<uuid:pk>/status/", trip_status, name="trip-status"),

    # Driver trip APIs
    path("available/", DriverAvailableTripsView.as_view(), name="driver-available-trips"),
    path("my-trips/", DriverMyTripsView.as_view(), name="driver-my-trips"),
    path("history/", DriverTripHistoryView.as_view(), name="driver-trip-history"),
    path("<uuid:pk>/accept/", accept_trip, name="accept-trip"),
    path("<uuid:pk>/update-status/", update_trip_status, name="update-trip-status"),
    path("update-location/", update_driver_location, name="update-driver-location"),
]
