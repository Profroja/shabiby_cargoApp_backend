from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone

from auths.models import User
from commissions.models import DriverCommissionBand, get_driver_commission
from drivers.models import Driver, DriverFeedback, DriverPayment, DriverSubscription
from drivers.performance import LEVELS, accounts_for, driver_account, trip_split
from farezones.models import FareZone
from orders.models import CargoOrder
from stations.models import CargoStation
from stations.views import _fetch_cargo_centers, fetch_external_for_import
from trips.models import CargoTrip


def _get_station_name_map():
    data = _fetch_cargo_centers(active_only=False)
    if not data:
        return {}
    return {
        str(item.get("id")): item.get("center_name", "") or item.get("name", "")
        for item in data
    }


def is_admin(user):
    """Global admin: sees and manages everything."""
    return user.is_authenticated and user.is_active and user.role == "admin"


def is_panel_user(user):
    """Global admins, plus station staff that are assigned to a station."""
    return is_admin(user) or (
        user.is_authenticated and user.is_active and user.role == "agent" and user.station_id is not None
    )


def _scoped_orders(user):
    """All orders for admins; staff only see orders leaving from or going to their station."""
    qs = CargoOrder.objects.all()
    if not is_admin(user):
        station_id = str(user.station_id)
        qs = qs.filter(Q(origin_station=station_id) | Q(destination_station=station_id))
    return qs


def admin_login(request):
    if is_panel_user(request.user):
        return redirect("adminpanel:dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user and is_panel_user(user):
            login(request, user)
            return redirect("adminpanel:dashboard")
        if user and user.role == "agent":
            error = "Your account is not assigned to a cargo station yet. Ask an admin."
        else:
            error = "Invalid credentials or not a staff account."
        return render(request, "adminpanel/login.html", {"error": error})
    return render(request, "adminpanel/login.html")


def admin_logout(request):
    logout(request)
    return redirect("adminpanel:login")


@login_required
@user_passes_test(is_panel_user)
def dashboard(request):
    if not is_admin(request.user):
        orders = _scoped_orders(request.user)
        station_id = str(request.user.station_id)
        return render(request, "adminpanel/dashboard.html", {
            "station": request.user.station,
            "total_orders": orders.count(),
            "awaiting_fare": orders.filter(shipping_fare_status=CargoOrder.ShippingFareStatus.PENDING).count(),
            "at_station": orders.filter(origin_station=station_id, status=CargoOrder.Status.AT_ORIGIN_STATION).count(),
            "incoming": orders.filter(destination_station=station_id, status=CargoOrder.Status.IN_TRANSIT).count(),
            "ready_for_collection": orders.filter(
                destination_station=station_id, status=CargoOrder.Status.ARRIVED_AT_DESTINATION
            ).count(),
        })
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
def customer_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    customer = get_object_or_404(User, pk=pk)
    if customer.role == "admin":
        return JsonResponse({"error": "Cannot delete admin user"}, status=400)
    customer.delete()
    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_admin)
def driver_list(request):
    status_filter = request.GET.get("status", "")
    drivers = Driver.objects.select_related("user", "vehicle_type", "station").order_by("-created_at")
    if status_filter:
        drivers = drivers.filter(approval_status=status_filter)
    drivers = list(drivers)
    accounts = accounts_for(drivers)
    for driver in drivers:
        driver.account = accounts[driver.id]
    return render(request, "adminpanel/drivers.html", {"drivers": drivers, "status_filter": status_filter})


@login_required
@user_passes_test(is_admin)
def driver_detail(request, pk):
    driver = get_object_or_404(Driver.objects.select_related("user", "vehicle_type", "station"), pk=pk)
    trips = list(
        driver.trips.select_related("order", "order__customer").order_by("-created_at")
    )
    station_map = _get_station_name_map()
    for trip in trips:
        trip.station_name = station_map.get(str(trip.destination_station), trip.destination_station)
        if trip.status == "delivered_to_station":
            _fare, trip.split_driver, trip.split_company = trip_split(trip)

    ratings = [
        {
            "source": "Customer",
            "category": "good" if r.stars >= 4 else "bad" if r.stars <= 2 else "neutral",
            "stars": r.stars,
            "comment": r.comment,
            "who": r.customer.first_name or r.customer.username,
            "created_at": r.created_at,
            "feedback": None,
        }
        for r in driver.ratings.select_related("customer")
    ]
    ratings += [
        {
            "source": "Admin",
            "category": f.category,
            "stars": f.stars,
            "comment": f.comment,
            "who": (f.recorded_by.first_name or f.recorded_by.username) if f.recorded_by else "Admin",
            "created_at": f.created_at,
            "feedback": f,
        }
        for f in driver.feedback.select_related("recorded_by")
    ]
    ratings.sort(key=lambda r: r["created_at"], reverse=True)

    return render(request, "adminpanel/driver_detail.html", {
        "driver": driver,
        "account": driver_account(driver),
        "trips": trips,
        "payments": driver.payments.select_related("recorded_by"),
        "subscriptions": driver.subscriptions.select_related("created_by"),
        "ratings": ratings,
        "levels": LEVELS,
        "today": timezone.localdate(),
        "stations": CargoStation.objects.filter(is_active=True).order_by("name"),
    })


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
@user_passes_test(is_panel_user)
def order_list(request):
    orders = _scoped_orders(request.user).select_related("customer").order_by("-created_at")
    station_map = _get_station_name_map()
    for order in orders:
        order.origin_station_name = station_map.get(str(order.origin_station), order.origin_station)
        order.destination_station_name = station_map.get(str(order.destination_station), order.destination_station)
    return render(request, "adminpanel/orders.html", {"orders": orders})


@login_required
@user_passes_test(is_panel_user)
def order_detail(request, pk):
    order = get_object_or_404(_scoped_orders(request.user).select_related("customer"), pk=pk)
    pickup_trip = CargoTrip.objects.filter(order=order, leg_type=CargoTrip.LegType.PICKUP).first()
    station_map = _get_station_name_map()
    order.origin_station_name = station_map.get(str(order.origin_station), order.origin_station)
    order.destination_station_name = station_map.get(str(order.destination_station), order.destination_station)

    commission_percent = None
    commission_amount = None
    if pickup_trip:
        commission_percent, commission_amount = get_driver_commission(
            pickup_trip.distance_km, pickup_trip.fare_amount
        )

    return render(
        request,
        "adminpanel/order_detail.html",
        {
            "order": order,
            "pickup_trip": pickup_trip,
            "commission_percent": commission_percent,
            "commission_amount": commission_amount,
        },
    )


@login_required
@user_passes_test(is_panel_user)
def order_set_fare(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    order = get_object_or_404(_scoped_orders(request.user), pk=pk)
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
@user_passes_test(is_panel_user)
def order_update_status(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    order = get_object_or_404(_scoped_orders(request.user), pk=pk)
    error = order.advance_station_status(request.POST.get("status"))
    if error:
        return JsonResponse({"error": error}, status=400)
    return JsonResponse({"ok": True, "status": order.status})


@login_required
@user_passes_test(is_panel_user)
def trip_list(request):
    trips = CargoTrip.objects.select_related("order", "order__customer", "driver", "driver__user").order_by("-created_at")
    if not is_admin(request.user):
        trips = trips.filter(order__in=_scoped_orders(request.user))
    return render(request, "adminpanel/trips.html", {"trips": trips})


@login_required
@user_passes_test(is_admin)
def order_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    order = get_object_or_404(CargoOrder, pk=pk)
    order.delete()
    return JsonResponse({"ok": True})


def _parse_commission_form(post):
    """Return (min_distance, max_distance, percent, is_active) or raise ValueError."""
    from decimal import Decimal, InvalidOperation

    try:
        min_dist = str(post.get("min_distance_km", "")).strip()
        max_dist = str(post.get("max_distance_km", "")).strip()
        percent = str(post.get("commission_percent", "")).strip()
        if not min_dist or not percent:
            raise ValueError("min_distance_km and commission_percent are required.")
        min_dec = Decimal(min_dist)
        max_dec = Decimal(max_dist) if max_dist else None
        per_dec = Decimal(percent)
        if max_dec is not None and max_dec < min_dec:
            raise ValueError("max_distance_km cannot be less than min_distance_km.")
        if per_dec < 0:
            raise ValueError("commission_percent must not be negative.")
    except InvalidOperation:
        raise ValueError("Invalid numeric values.")
    return min_dec, max_dec, per_dec, post.get("is_active") == "on"


@login_required
@user_passes_test(is_admin)
def commission_list(request):
    bands = DriverCommissionBand.objects.all().order_by("min_distance_km")

    if request.method == "POST":
        try:
            min_dec, max_dec, per_dec, is_active = _parse_commission_form(request.POST)
        except ValueError as e:
            return render(
                request,
                "adminpanel/commissions.html",
                {"bands": bands, "error": str(e)},
            )
        DriverCommissionBand.objects.create(
            min_distance_km=min_dec,
            max_distance_km=max_dec,
            commission_percent=per_dec,
            is_active=is_active,
        )
        return redirect("adminpanel:commissions")

    return render(request, "adminpanel/commissions.html", {"bands": bands})


@login_required
@user_passes_test(is_admin)
def commission_edit(request, pk):
    band = get_object_or_404(DriverCommissionBand, pk=pk)
    if request.method == "POST":
        try:
            min_dec, max_dec, per_dec, is_active = _parse_commission_form(request.POST)
        except ValueError as e:
            return render(
                request,
                "adminpanel/commission_edit.html",
                {"band": band, "error": str(e)},
            )
        band.min_distance_km = min_dec
        band.max_distance_km = max_dec
        band.commission_percent = per_dec
        band.is_active = is_active
        band.save(
            update_fields=[
                "min_distance_km",
                "max_distance_km",
                "commission_percent",
                "is_active",
                "updated_at",
            ]
        )
        return redirect("adminpanel:commissions")

    return render(request, "adminpanel/commission_edit.html", {"band": band})


@login_required
@user_passes_test(is_admin)
def commission_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    band = get_object_or_404(DriverCommissionBand, pk=pk)
    band.delete()
    return JsonResponse({"ok": True})


# ---------- Cargo stations ----------

def _parse_station_form(post):
    """Return the cleaned station fields, or raise ValueError with a message."""
    from decimal import Decimal, InvalidOperation

    name = post.get("name", "").strip()
    branch_code = post.get("branch_code", "").strip().upper()
    if not name or not branch_code:
        raise ValueError("Station name and branch code are required.")
    if len(branch_code) > 10:
        raise ValueError("Branch code must be 10 characters or fewer.")

    coords = {}
    for field, low, high in (("latitude", -90, 90), ("longitude", -180, 180)):
        raw = post.get(field, "").strip()
        if not raw:
            coords[field] = None
            continue
        try:
            value = Decimal(raw).quantize(Decimal("0.000001"))
        except InvalidOperation:
            raise ValueError(f"{field.capitalize()} must be a number.")
        if not low <= value <= high:
            raise ValueError(f"{field.capitalize()} must be between {low} and {high}.")
        coords[field] = value
    if (coords["latitude"] is None) != (coords["longitude"] is None):
        raise ValueError("Enter both latitude and longitude, or leave both empty.")

    prices = {}
    for field, label in (("price_per_km", "Price per km"), ("min_fare", "Minimum fare")):
        raw = post.get(field, "").strip().replace(",", "")
        if not raw:
            prices[field] = None
            continue
        try:
            value = Decimal(raw).quantize(Decimal("0.01"))
        except InvalidOperation:
            raise ValueError(f"{label} must be a number.")
        if value < 0:
            raise ValueError(f"{label} can't be negative.")
        prices[field] = value

    zone_id = post.get("zone", "").strip()
    return {
        "name": name,
        "branch_code": branch_code,
        "region": post.get("region", "").strip(),
        "city": post.get("city", "").strip(),
        "address": post.get("address", "").strip(),
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "price_per_km": prices["price_per_km"],
        "min_fare": prices["min_fare"],
        "zone_id": int(zone_id) if zone_id.isdigit() else None,
        "is_active": post.get("is_active") == "on",
    }


def _station_page(request, error=None, form=None, status=200):
    stations = CargoStation.objects.select_related("zone").order_by("name")
    return render(
        request,
        "adminpanel/stations.html",
        {
            "stations": stations,
            "zones": FareZone.objects.filter(is_active=True).order_by("name"),
            "missing_coords": stations.filter(latitude__isnull=True).count(),
            "error": error,
            "form": form or {},
            "notice": request.GET.get("notice", ""),
        },
        status=status,
    )


@login_required
@user_passes_test(is_admin)
def station_list(request):
    if request.method == "POST":
        try:
            data = _parse_station_form(request.POST)
        except ValueError as e:
            return _station_page(request, error=str(e), form=request.POST, status=400)
        if CargoStation.objects.filter(branch_code=data["branch_code"]).exists():
            return _station_page(
                request,
                error=f"A station with branch code {data['branch_code']} already exists.",
                form=request.POST,
                status=400,
            )
        CargoStation.objects.create(**data)
        return redirect("adminpanel:stations")
    return _station_page(request)


@login_required
@user_passes_test(is_admin)
def station_edit(request, pk):
    station = get_object_or_404(CargoStation, pk=pk)
    context = {"station": station, "zones": FareZone.objects.filter(is_active=True).order_by("name")}
    if request.method == "POST":
        try:
            data = _parse_station_form(request.POST)
        except ValueError as e:
            return render(request, "adminpanel/station_edit.html", {**context, "error": str(e)}, status=400)
        if CargoStation.objects.filter(branch_code=data["branch_code"]).exclude(pk=station.pk).exists():
            error = f"Another station already uses branch code {data['branch_code']}."
            return render(request, "adminpanel/station_edit.html", {**context, "error": error}, status=400)
        for field, value in data.items():
            setattr(station, field, value)
        station.save()
        return redirect("adminpanel:stations")
    return render(request, "adminpanel/station_edit.html", context)


@login_required
@user_passes_test(is_admin)
def station_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    station = get_object_or_404(CargoStation, pk=pk)
    station_id = str(station.pk)
    if CargoOrder.objects.filter(origin_station=station_id).exists() or CargoOrder.objects.filter(
        destination_station=station_id
    ).exists():
        return JsonResponse(
            {"error": "This station is used by existing orders. Set it to inactive instead of deleting it."},
            status=400,
        )
    station.delete()
    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_admin)
def station_toggle(request, pk):
    """Turn a station on or off in the apps."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    station = get_object_or_404(CargoStation, pk=pk)
    station.is_active = not station.is_active
    station.save(update_fields=["is_active", "updated_at"])
    return JsonResponse({"ok": True, "is_active": station.is_active})


@login_required
@user_passes_test(is_admin)
def station_import(request):
    """Copy the main Shabiby system's stations in. Existing branch codes are skipped."""
    if request.method != "POST":
        return redirect("adminpanel:stations")
    centers = fetch_external_for_import()
    if centers is None:
        return _station_page(request, error="Could not reach the main Shabiby system. Try again later.", status=502)

    created = 0
    for item in centers:
        code = (item.get("branch_code") or "").strip().upper()[:10]
        name = (item.get("center_name") or item.get("name") or "").strip()
        if not code or not name or CargoStation.objects.filter(branch_code=code).exists():
            continue
        # Locations look like "KARIAKOO , Dar es Salaam" or "MAFINGA-Iringa".
        parts = [p.strip() for p in (item.get("location") or "").replace("-", ",").split(",") if p.strip()]
        has_coords = item.get("latitude") is not None and item.get("longitude") is not None
        CargoStation.objects.create(
            name=name,
            branch_code=code,
            city=parts[0] if len(parts) > 1 else "",
            region=parts[-1] if parts else "",
            latitude=item["latitude"] if has_coords else None,
            longitude=item["longitude"] if has_coords else None,
            is_active=item.get("is_active", True),
        )
        created += 1
    return redirect(f"{reverse('adminpanel:stations')}?notice=Imported {created} station(s).")


# ---------- Staff users ----------

STAFF_ROLES = ("admin", "agent")


def _staff_page(request, error=None, status=200):
    return render(
        request,
        "adminpanel/staff.html",
        {
            "staff": User.objects.filter(role__in=STAFF_ROLES).select_related("station").order_by("role", "first_name"),
            "stations": CargoStation.objects.filter(is_active=True).order_by("name"),
            "error": error,
        },
        status=status,
    )


def _parse_staff_form(post, editing=None):
    """Return cleaned fields (password may be None when editing), or raise ValueError."""
    first_name = post.get("first_name", "").strip()
    last_name = post.get("last_name", "").strip()
    username = post.get("username", "").strip()
    phone = post.get("phone_number", "").strip() or None
    email = post.get("email", "").strip() or None
    role = post.get("role", "agent")
    password = post.get("password", "")
    station_id = post.get("station", "").strip()

    if not first_name or not username:
        raise ValueError("First name and username are required.")
    if role not in STAFF_ROLES:
        raise ValueError("Choose a valid role.")
    station = None
    if role == "agent":
        station = CargoStation.objects.filter(pk=station_id).first() if station_id else None
        if station is None:
            raise ValueError("Station staff must be assigned to a cargo station.")
    if editing is None and len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if editing is not None and password and len(password) < 6:
        raise ValueError("New password must be at least 6 characters.")

    others = User.objects.exclude(pk=editing.pk) if editing else User.objects.all()
    if others.filter(username=username).exists():
        raise ValueError(f"The username '{username}' is already taken.")
    if phone and others.filter(phone_number=phone).exists():
        raise ValueError(f"The phone number {phone} already belongs to another account.")
    if email and others.filter(email=email).exists():
        raise ValueError(f"The email {email} already belongs to another account.")

    return {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "phone_number": phone,
        "email": email,
        "role": role,
        "station": station,
        "password": password or None,
    }


@login_required
@user_passes_test(is_admin)
def staff_list(request):
    if request.method == "POST":
        try:
            data = _parse_staff_form(request.POST)
        except ValueError as e:
            return _staff_page(request, error=str(e), status=400)
        password = data.pop("password")
        User.objects.create_user(password=password, is_active=True, **data)
        return redirect("adminpanel:staff")
    return _staff_page(request)


@login_required
@user_passes_test(is_admin)
def staff_edit(request, pk):
    if request.method != "POST":
        return redirect("adminpanel:staff")
    member = get_object_or_404(User, pk=pk, role__in=STAFF_ROLES)
    try:
        data = _parse_staff_form(request.POST, editing=member)
    except ValueError as e:
        return _staff_page(request, error=str(e), status=400)
    if member.pk == request.user.pk and data["role"] != "admin":
        return _staff_page(request, error="You can't remove your own admin access.", status=400)
    password = data.pop("password")
    for field, value in data.items():
        setattr(member, field, value)
    if password:
        member.set_password(password)
    member.save()
    return redirect("adminpanel:staff")


@login_required
@user_passes_test(is_admin)
def staff_toggle(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    member = get_object_or_404(User, pk=pk, role__in=STAFF_ROLES)
    if member.pk == request.user.pk:
        return JsonResponse({"error": "You can't deactivate your own account."}, status=400)
    member.is_active = not member.is_active
    member.save(update_fields=["is_active", "updated_at"])
    return JsonResponse({"ok": True, "is_active": member.is_active})


@login_required
@user_passes_test(is_admin)
def staff_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    member = get_object_or_404(User, pk=pk, role__in=STAFF_ROLES)
    if member.pk == request.user.pk:
        return JsonResponse({"error": "You can't delete your own account."}, status=400)
    member.delete()
    return JsonResponse({"ok": True})


# ---------- Driver accounts: payments, subscriptions, feedback ----------

def _money(raw, label, allow_zero=False):
    from decimal import Decimal, InvalidOperation

    try:
        value = Decimal(str(raw).replace(",", "").strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a number.")
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"{label} must be greater than zero.")
    return value


def _date(raw, label, required=True):
    from datetime import date

    raw = (raw or "").strip()
    if not raw:
        if required:
            raise ValueError(f"{label} is required.")
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"{label} must be a valid date.")


def _json_error(e):
    return JsonResponse({"error": str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
def driver_payments(request):
    """All drivers' balances: what they owe and what they have paid."""
    drivers = list(Driver.objects.select_related("user").order_by("user__first_name"))
    accounts = accounts_for(drivers)
    rows = [{"driver": d, "account": accounts[d.id]} for d in drivers]
    show = request.GET.get("show", "owing")
    if show == "owing":
        rows = [r for r in rows if r["account"]["balance_due"] > 0]
    rows.sort(key=lambda r: r["account"]["balance_due"], reverse=True)
    totals = {
        key: sum((a[key] for a in accounts.values()), Decimal("0"))
        for key in ("fares_total", "company_total", "paid_total", "balance_due")
    }
    return render(request, "adminpanel/driver_payments.html", {
        "rows": rows, "show": show, "totals": totals, "today": timezone.localdate(),
    })


@login_required
@user_passes_test(is_admin)
def driver_payment_add(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    driver = get_object_or_404(Driver, pk=pk)
    try:
        kind = request.POST.get("kind", "commission")
        if kind not in DriverPayment.Kind.values:
            raise ValueError("Choose what the payment is for.")
        method = request.POST.get("method", "cash")
        if method not in DriverPayment.Method.values:
            raise ValueError("Choose a payment method.")
        payment = DriverPayment.objects.create(
            driver=driver,
            kind=kind,
            amount=_money(request.POST.get("amount", ""), "Amount"),
            method=method,
            reference=request.POST.get("reference", "").strip()[:100],
            note=request.POST.get("note", "").strip(),
            paid_on=_date(request.POST.get("paid_on"), "Payment date"),
            recorded_by=request.user,
        )
    except ValueError as e:
        return _json_error(e)
    return JsonResponse({"ok": True, "id": str(payment.pk), "balance_due": str(driver_account(driver)["balance_due"])})


@login_required
@user_passes_test(is_admin)
def driver_payment_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    get_object_or_404(DriverPayment, pk=pk).delete()
    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_admin)
def driver_subscription_add(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    driver = get_object_or_404(Driver, pk=pk)
    try:
        plan = request.POST.get("plan", "free")
        if plan not in DriverSubscription.Plan.values:
            raise ValueError("Choose Free or Paid.")
        starts_on = _date(request.POST.get("starts_on"), "Start date")
        ends_on = _date(request.POST.get("ends_on"), "End date", required=plan == "paid")
        if ends_on and ends_on < starts_on:
            raise ValueError("The end date must be after the start date.")
        fee = _money(request.POST.get("fee") or "0", "Fee", allow_zero=True) if plan == "paid" else 0
        if plan == "paid" and fee == 0:
            raise ValueError("Enter the fee for a paid subscription.")
        DriverSubscription.objects.create(
            driver=driver, plan=plan, starts_on=starts_on, ends_on=ends_on, fee=fee,
            note=request.POST.get("note", "").strip(), created_by=request.user,
        )
    except ValueError as e:
        return _json_error(e)
    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_admin)
def driver_subscription_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    get_object_or_404(DriverSubscription, pk=pk).delete()
    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_admin)
def driver_feedback_add(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    driver = get_object_or_404(Driver, pk=pk)
    try:
        category = request.POST.get("category", "")
        if category not in DriverFeedback.Category.values:
            raise ValueError("Choose Good, Bad or Issue.")
        raw_stars = request.POST.get("stars", "").strip()
        stars = int(raw_stars) if raw_stars else None
        if stars is not None and not 1 <= stars <= 5:
            raise ValueError("Stars must be between 1 and 5.")
        comment = request.POST.get("comment", "").strip()
        if not comment:
            raise ValueError("Write a short comment.")
        trip_id = request.POST.get("trip", "").strip()
        trip = driver.trips.filter(pk=trip_id).first() if trip_id else None
        DriverFeedback.objects.create(
            driver=driver, trip=trip, category=category, stars=stars,
            comment=comment, recorded_by=request.user,
        )
    except ValueError as e:
        return _json_error(e)
    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_admin)
def driver_feedback_resolve(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    feedback = get_object_or_404(DriverFeedback, pk=pk, category="issue")
    feedback.is_resolved = not feedback.is_resolved
    feedback.save()
    return JsonResponse({"ok": True, "is_resolved": feedback.is_resolved})


@login_required
@user_passes_test(is_admin)
def driver_feedback_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    get_object_or_404(DriverFeedback, pk=pk).delete()
    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_admin)
def driver_set_station(request, pk):
    """Assign the cargo station whose pickup requests this driver receives."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    driver = get_object_or_404(Driver, pk=pk)
    station_id = request.POST.get("station", "").strip()
    station = CargoStation.objects.filter(pk=station_id).first() if station_id else None
    if station_id and station is None:
        return JsonResponse({"error": "Station not found."}, status=400)
    driver.station = station
    driver.region = station.name if station else ""
    driver.save(update_fields=["station", "region", "updated_at"])
    return JsonResponse({"ok": True, "station": station.name if station else ""})
