from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("login/", views.admin_login, name="login"),
    path("logout/", views.admin_logout, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("customers/", views.customer_list, name="customers"),
    path("customers/<uuid:pk>/delete/", views.customer_delete, name="customer-delete"),
    path("drivers/", views.driver_list, name="drivers"),
    path("drivers/<uuid:pk>/", views.driver_detail, name="driver-detail"),
    path("drivers/<uuid:pk>/approve/", views.driver_approve, name="driver-approve"),
    path("drivers/<uuid:pk>/delete/", views.driver_delete, name="driver-delete"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<uuid:pk>/", views.order_detail, name="order-detail"),
    path("orders/<uuid:pk>/set-fare/", views.order_set_fare, name="order-set-fare"),
    path("orders/<uuid:pk>/delete/", views.order_delete, name="order-delete"),
    path("trips/", views.trip_list, name="trips"),
]
