from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Driver
from .serializers import DriverProfileSerializer, DriverRegistrationSerializer

User = get_user_model()


def _jwt_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class DriverRegisterView(generics.CreateAPIView):
    """
    Combined driver registration after OTP verification.
    Accepts: first_name, middle_name, last_name, vehicle_type, vehicle_name,
             vehicle_color, license_plate, license_number, license_photo, profile_photo
    Requires authentication (temp JWT from verify-otp).
    Content-Type: multipart/form-data
    """
    serializer_class = DriverRegistrationSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"error": "Authentication required. Verify OTP first."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if hasattr(user, "driver"):
            return Response(
                {"error": "Driver profile already exists. Use PATCH /api/drivers/me/ to update."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Update user with names and driver role
        user.first_name = data["first_name"]
        user.middle_name = data.get("middle_name", "")
        user.last_name = data["last_name"]
        user.role = "driver"
        user.save(update_fields=["first_name", "middle_name", "last_name", "role"])

        # Create driver profile
        from vehicles.models import VehicleType
        try:
            vehicle_type = VehicleType.objects.get(id=data["vehicle_type"])
        except VehicleType.DoesNotExist:
            return Response(
                {"error": f"Vehicle type {data['vehicle_type']} not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        driver = Driver.objects.create(
            user=user,
            vehicle_type=vehicle_type,
            vehicle_name=data.get("vehicle_name", ""),
            vehicle_color=data.get("vehicle_color", ""),
            license_plate=data["license_plate"],
            license_number=data["license_number"],
            license_photo=data["license_photo"],
            profile_photo=data["profile_photo"],
        )

        # Issue fresh JWT tokens
        tokens = _jwt_for_user(user)

        output = DriverProfileSerializer(driver, context={"request": request})
        response_data = output.data
        response_data["tokens"] = tokens
        return Response(response_data, status=status.HTTP_201_CREATED)


class DriverMeView(generics.RetrieveUpdateAPIView):
    serializer_class = DriverProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return getattr(self.request.user, "driver", None)

    def retrieve(self, request, *args, **kwargs):
        driver = self.get_object()
        if not driver:
            return Response(
                {"error": "No driver profile found. Please complete driver registration."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(driver, context={"request": request})
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        driver = self.get_object()
        if not driver:
            return Response(
                {"error": "No driver profile found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(
            driver, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DriverListView(generics.ListAPIView):
    serializer_class = DriverProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Driver.objects.select_related("user", "vehicle_type").all()
        status_filter = self.request.query_params.get("approval_status")
        if status_filter:
            qs = qs.filter(approval_status=status_filter)
        return qs

    def list(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


class DriverDetailView(generics.RetrieveAPIView):
    serializer_class = DriverProfileSerializer
    permission_classes = [IsAuthenticated]
    queryset = Driver.objects.all()

    def retrieve(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={"request": request})
        return Response(serializer.data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def approve_driver(request, pk):
    if request.user.role != "admin":
        return Response(
            {"error": "Admin access required."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        driver = Driver.objects.get(pk=pk)
    except Driver.DoesNotExist:
        return Response(
            {"error": "Driver not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    new_status = request.data.get("approval_status")
    if new_status not in ("approved", "rejected"):
        return Response(
            {"error": "approval_status must be 'approved' or 'rejected'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    driver.approval_status = new_status
    driver.is_verified = (new_status == "approved")
    driver.save(update_fields=["approval_status", "is_verified", "updated_at"])

    serializer = DriverProfileSerializer(driver, context={"request": request})
    return Response(serializer.data)
