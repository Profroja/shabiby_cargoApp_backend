from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("login/", views.admin_login, name="login"),
    path("logout/", views.admin_logout, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("customers/", views.customer_list, name="customers"),
    path("drivers/", views.driver_list, name="drivers"),
    path("drivers/<uuid:pk>/", views.driver_detail, name="driver-detail"),
    path("drivers/<uuid:pk>/approve/", views.driver_approve, name="driver-approve"),
    path("orders/", views.order_list, name="orders"),
    path("trips/", views.trip_list, name="trips"),
]
