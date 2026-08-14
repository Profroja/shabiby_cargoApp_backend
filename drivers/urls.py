from django.urls import path

from .views import (
    DriverDetailView,
    DriverListView,
    DriverMeView,
    DriverRegisterView,
    approve_driver,
)

urlpatterns = [
    path("register/", DriverRegisterView.as_view(), name="driver-register"),
    path("me/", DriverMeView.as_view(), name="driver-me"),
    path("", DriverListView.as_view(), name="driver-list"),
    path("<uuid:pk>/", DriverDetailView.as_view(), name="driver-detail"),
    path("<uuid:pk>/approve/", approve_driver, name="driver-approve"),
]
