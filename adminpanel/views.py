from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse

from auths.models import User
from drivers.models import Driver
from orders.models import CargoOrder
from trips.models import CargoTrip


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


def admin_login(request):
    if request.user.is_authenticated and request.user.role == "admin":
        return redirect("adminpanel:dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user and user.role == "admin":
            login(request, user)
            return redirect("adminpanel:dashboard")
        return render(request, "adminpanel/login.html", {"error": "Invalid credentials or not an admin account."})
    return render(request, "adminpanel/login.html")


def admin_logout(request):
    logout(request)
    return redirect("adminpanel:login")


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    total_customers = User.objects.filter(role="customer").count()
    total_drivers = Driver.objects.count()
    pending_drivers = Driver.objects.filter(approval_status="pending").count()
    approved_drivers = Driver.objects.filter(approval_status="approved").count()
    total_orders = CargoOrder.objects.count()
    total_trips = CargoTrip.objects.count()
    active_trips = CargoTrip.objects.exclude(status__in=["delivered_to_station", "cancelled"]).count()

    context = {
        "total_customers": total_customers,
        "total_drivers": total_drivers,
        "pending_drivers": pending_drivers,
        "approved_drivers": approved_drivers,
        "total_orders": total_orders,
        "total_trips": total_trips,
        "active_trips": active_trips,
    }
    return render(request, "adminpanel/dashboard.html", context)


@login_required
@user_passes_test(is_admin)
def customer_list(request):
    from django.db.models import Q
    # Show users with role=customer OR users who have placed orders
    customer_ids = CargoOrder.objects.values_list("customer_id", flat=True).distinct()
    customers = User.objects.filter(
        Q(role="customer") | Q(id__in=customer_ids)
    ).order_by("-created_at")
    return render(request, "adminpanel/customers.html", {"customers": customers})


@login_required
@user_passes_test(is_admin)
def driver_list(request):
    status_filter = request.GET.get("status", "")
    drivers = Driver.objects.select_related("user", "vehicle_type").order_by("-created_at")
    if status_filter:
        drivers = drivers.filter(approval_status=status_filter)
    return render(request, "adminpanel/drivers.html", {"drivers": drivers, "status_filter": status_filter})


@login_required
@user_passes_test(is_admin)
def driver_detail(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    return render(request, "adminpanel/driver_detail.html", {"driver": driver})


@login_required
@user_passes_test(is_admin)
def driver_approve(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    driver = get_object_or_404(Driver, pk=pk)
    new_status = request.POST.get("approval_status")
    if new_status not in ("approved", "rejected"):
        return JsonResponse({"error": "Invalid status"}, status=400)
    driver.approval_status = new_status
    driver.is_verified = (new_status == "approved")
    driver.save(update_fields=["approval_status", "is_verified", "updated_at"])
    return JsonResponse({"ok": True, "approval_status": new_status})


@login_required
@user_passes_test(is_admin)
def driver_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    driver = get_object_or_404(Driver, pk=pk)
    driver.delete()
    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_admin)
def order_list(request):
    orders = CargoOrder.objects.select_related("customer").order_by("-created_at")
    return render(request, "adminpanel/orders.html", {"orders": orders})


@login_required
@user_passes_test(is_admin)
def order_detail(request, pk):
    order = get_object_or_404(CargoOrder.objects.select_related("customer"), pk=pk)
    pickup_trip = CargoTrip.objects.filter(order=order, leg_type=CargoTrip.LegType.PICKUP).first()
    return render(request, "adminpanel/order_detail.html", {"order": order, "pickup_trip": pickup_trip})


@login_required
@user_passes_test(is_admin)
def order_set_fare(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    order = get_object_or_404(CargoOrder, pk=pk)
    fare = request.POST.get("shipping_fare")
    if not fare:
        return JsonResponse({"error": "shipping_fare is required"}, status=400)
    try:
        from decimal import Decimal, InvalidOperation
        order.shipping_fare = Decimal(str(fare))
    except (InvalidOperation, ValueError):
        return JsonResponse({"error": "Invalid fare amount"}, status=400)
    order.shipping_fare_status = CargoOrder.ShippingFareStatus.PRICED
    order.save(update_fields=["shipping_fare", "shipping_fare_status", "updated_at"])
    return JsonResponse({"ok": True, "shipping_fare": str(order.shipping_fare), "shipping_fare_status": order.shipping_fare_status})


@login_required
@user_passes_test(is_admin)
def trip_list(request):
    trips = CargoTrip.objects.select_related("order", "order__customer", "driver", "driver__user").order_by("-created_at")
    return render(request, "adminpanel/trips.html", {"trips": trips})


@login_required
@user_passes_test(is_admin)
def order_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    order = get_object_or_404(CargoOrder, pk=pk)
    order.delete()
    return JsonResponse({"ok": True})
