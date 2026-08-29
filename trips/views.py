from datetime import timezone
import logging

from django.db.models import Q
from django.utils import timezone as tz_utils
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drivers.models import Driver
from orders.models import CargoOrder

from .models import CargoTrip
from .serializers import CargoTripSerializer

logger = logging.getLogger(__name__)


class CargoTripListView(generics.ListCreateAPIView):
    serializer_class = CargoTripSerializer

    def get_queryset(self):
        return CargoTrip.objects.filter(order__customer=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        logger.error(f"[CargoTripListView] POST data: {request.data}")
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"[CargoTripListView] Error creating trip: {e}")
            raise


class CargoTripDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CargoTripSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "driver":
            return CargoTrip.objects.filter(driver__user=user)
        return CargoTrip.objects.filter(order__customer=user)


# ---------- Driver trip APIs ----------

class DriverAvailableTripsView(generics.ListAPIView):
    """List trips with no driver assigned, available for the logged-in driver.
    Filters by driver's region (nearest cargo center name)."""
    serializer_class = CargoTripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        logger.error(f"[DriverAvailableTripsView] User: {self.request.user.phone_number}, Role: {self.request.user.role}")
        if self.request.user.role != "driver":
            logger.error(f"[DriverAvailableTripsView] User is not a driver, returning empty queryset")
            return CargoTrip.objects.none()

        try:
            driver = self.request.user.driver
        except Driver.DoesNotExist:
            return CargoTrip.objects.none()

        trips = CargoTrip.objects.filter(
            driver__isnull=True,
            status__in=["requested", "searching_driver"],
        ).select_related("order", "order__customer").order_by("-created_at")

        # Filter by driver's region: match trip's destination_station (nearest cargo
        # center to the customer's pickup) to the driver's registered region.
        driver_region = (driver.region or "").strip()
        if driver_region:
            from stations.views import _get_center_map
            center_map = _get_center_map()
            # Find cargo center IDs whose center_name matches the driver's region
            matching_station_ids = [
                sid for sid, cdata in center_map.items()
                if (cdata.get("center_name", "") or cdata.get("name", "")).strip().lower() == driver_region.lower()
            ]
            if matching_station_ids:
                trips = trips.filter(destination_station__in=matching_station_ids)
            else:
                # No matching stations found for driver's region — no trips
                logger.error(f"[DriverAvailableTripsView] No stations found for region '{driver_region}', returning empty")
                return CargoTrip.objects.none()

        logger.error(f"[DriverAvailableTripsView] Found {trips.count()} available trips for region '{driver_region}'")
        return trips


class DriverMyTripsView(generics.ListAPIView):
    """List trips assigned to the logged-in driver."""
    serializer_class = CargoTripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != "driver":
            return CargoTrip.objects.none()
        return CargoTrip.objects.filter(
            driver__user=self.request.user
        ).exclude(
            status__in=["delivered_to_station", "cancelled"]
        ).select_related("order", "order__customer", "driver", "driver__user").order_by("-created_at")


class DriverTripHistoryView(generics.ListAPIView):
    """List completed/cancelled trips for the logged-in driver."""
    serializer_class = CargoTripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != "driver":
            return CargoTrip.objects.none()
        return CargoTrip.objects.filter(
            driver__user=self.request.user,
            status__in=["delivered_to_station", "cancelled"],
        ).select_related("order", "order__customer").order_by("-delivered_at")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_trip(request, pk):
    """Driver accepts a trip. Sets driver, changes status to driver_assigned."""
    if request.user.role != "driver":
        return Response({"error": "Driver access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return Response({"error": "No driver profile found."}, status=status.HTTP_404_NOT_FOUND)

    if driver.approval_status != "approved":
        return Response({"error": "Driver not approved yet."}, status=status.HTTP_403_FORBIDDEN)

    trip = CargoTrip.objects.filter(pk=pk, driver__isnull=True, status__in=["requested", "searching_driver"]).first()
    if not trip:
        return Response({"error": "Trip not available."}, status=status.HTTP_404_NOT_FOUND)

    trip.driver = driver
    trip.status = CargoTrip.Status.DRIVER_ASSIGNED
    trip.driver_assigned_at = tz_utils.now()
    trip.save(update_fields=["driver", "status", "driver_assigned_at", "updated_at"])

    # Update order status
    order = trip.order
    if order.status == CargoOrder.Status.SUBMITTED:
        order.status = CargoOrder.Status.PICKUP_IN_PROGRESS
        order.save(update_fields=["status", "updated_at"])

    serializer = CargoTripSerializer(trip, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_trip_status(request, pk):
    """Driver updates trip status. Valid transitions only."""
    if request.user.role != "driver":
        return Response({"error": "Driver access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return Response({"error": "No driver profile found."}, status=status.HTTP_404_NOT_FOUND)

    trip = CargoTrip.objects.filter(pk=pk, driver=driver).first()
    if not trip:
        return Response({"error": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get("status")
    valid_statuses = [
        "en_route_to_pickup",
        "arrived_at_pickup",
        "picked_up",
        "delivered_to_station",
        "cancelled",
    ]
    if new_status not in valid_statuses:
        return Response({"error": f"Invalid status. Must be one of: {valid_statuses}"}, status=status.HTTP_400_BAD_REQUEST)

    now = tz_utils.now()
    update_fields = ["status", "updated_at"]

    trip.status = new_status
    if new_status == "arrived_at_pickup":
        trip.arrived_at_pickup_at = now
        update_fields.append("arrived_at_pickup_at")
    elif new_status == "picked_up":
        trip.picked_up_at = now
        update_fields.append("picked_up_at")
    elif new_status == "delivered_to_station":
        trip.delivered_at = now
        update_fields.append("delivered_at")
    elif new_status == "cancelled":
        trip.cancelled_at = now
        update_fields.append("cancelled_at")

    trip.save(update_fields=update_fields)

    # Update order status based on trip status
    order = trip.order
    if new_status == "picked_up":
        if order.status != CargoOrder.Status.PICKUP_IN_PROGRESS:
            order.status = CargoOrder.Status.PICKUP_IN_PROGRESS
            order.save(update_fields=["status", "updated_at"])
    elif new_status == "delivered_to_station":
        order.status = CargoOrder.Status.AT_ORIGIN_STATION
        order.save(update_fields=["status", "updated_at"])
    elif new_status == "cancelled":
        order.status = CargoOrder.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])

    serializer = CargoTripSerializer(trip, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_driver_location(request):
    """Driver updates their current location."""
    if request.user.role != "driver":
        return Response({"error": "Driver access required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return Response({"error": "No driver profile found."}, status=status.HTTP_404_NOT_FOUND)

    lat = request.data.get("latitude")
    lng = request.data.get("longitude")
    if lat is None or lng is None:
        return Response({"error": "latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)

    driver.current_latitude = lat
    driver.current_longitude = lng
    driver.last_location_at = tz_utils.now()
    driver.save(update_fields=["current_latitude", "current_longitude", "last_location_at", "updated_at"])

    return Response({"ok": True}, status=status.HTTP_200_OK)


# ---------- Customer rating API ----------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rate_driver(request, pk):
    """Customer rates the driver after trip delivery.
    pk is the trip ID."""
    if request.user.role != "customer":
        return Response({"error": "Customer access required."}, status=status.HTTP_403_FORBIDDEN)

    trip = CargoTrip.objects.filter(pk=pk, order__customer=request.user).first()
    if not trip:
        return Response({"error": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)

    if not trip.driver:
        return Response({"error": "No driver assigned to this trip."}, status=status.HTTP_400_BAD_REQUEST)

    if trip.status not in ["delivered_to_station", "cancelled"]:
        return Response({"error": "Trip must be delivered before rating."}, status=status.HTTP_400_BAD_REQUEST)

    from drivers.rating_models import DriverRating

    # Check if already rated
    existing = DriverRating.objects.filter(trip=trip, customer=request.user).first()
    if existing:
        return Response({"error": "You have already rated this trip."}, status=status.HTTP_400_BAD_REQUEST)

    stars = request.data.get("stars")
    comment = request.data.get("comment", "")

    if stars is None or not isinstance(stars, (int, float)) or stars < 1 or stars > 5:
        return Response({"error": "stars must be a number between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)

    rating = DriverRating.objects.create(
        driver=trip.driver,
        trip=trip,
        customer=request.user,
        stars=int(stars),
        comment=str(comment).strip(),
    )

    return Response({
        "id": str(rating.id),
        "stars": rating.stars,
        "comment": rating.comment,
        "driver_rating_avg": float(trip.driver.rating_avg),
        "driver_rating_count": trip.driver.rating_count,
    }, status=status.HTTP_201_CREATED)


# ---------- Customer trip polling API ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trip_status(request, pk):
    """Customer polls trip status with driver location. Returns full trip + driver info."""
    trip = CargoTrip.objects.filter(pk=pk, order__customer=request.user).first()
    if not trip:
        # Also allow driver to poll: own assigned trips or any still-available trip
        if request.user.role == "driver":
            trip = (
                CargoTrip.objects.filter(pk=pk, driver__user=request.user).first()
                or CargoTrip.objects.filter(
                    pk=pk,
                    driver__isnull=True,
                    status__in=["requested", "searching_driver"],
                ).first()
            )
        if not trip:
            return Response({"error": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = CargoTripSerializer(trip, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)
