from django.conf import settings
from rest_framework import serializers

from .models import Driver


class DriverProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    middle_name = serializers.CharField(source="user.middle_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    vehicle_type_name = serializers.CharField(source="vehicle_type.display_name", read_only=True, default="")
    license_photo = serializers.SerializerMethodField()
    license_photo_url = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = (
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "vehicle_type",
            "vehicle_type_name",
            "vehicle_name",
            "vehicle_color",
            "license_plate",
            "license_number",
            "national_id_number",
            "license_photo",
            "license_photo_url",
            "profile_photo",
            "profile_photo_url",
            "approval_status",
            "is_verified",
            "is_online",
            "rating_avg",
            "rating_count",
            "region",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "approval_status",
            "is_verified",
            "is_online",
            "rating_avg",
            "rating_count",
            "created_at",
            "updated_at",
        )

    def get_license_photo(self, obj):
        if obj.license_photo:
            return f"{settings.BASE_URL}/{obj.license_photo.url.lstrip('/')}"
        return None

    def get_license_photo_url(self, obj):
        if obj.license_photo:
            return f"{settings.BASE_URL}/{obj.license_photo.url.lstrip('/')}"
        return None

    def get_profile_photo(self, obj):
        if obj.profile_photo:
            return f"{settings.BASE_URL}/{obj.profile_photo.url.lstrip('/')}"
        return None

    def get_profile_photo_url(self, obj):
        if obj.profile_photo:
            return f"{settings.BASE_URL}/{obj.profile_photo.url.lstrip('/')}"
        return None


class DriverMeSerializer(DriverProfileSerializer):
    """The logged-in driver's profile plus their standing with the company."""

    account = serializers.SerializerMethodField()

    class Meta(DriverProfileSerializer.Meta):
        fields = DriverProfileSerializer.Meta.fields + ("account",)

    def get_account(self, obj):
        from .performance import driver_account

        a = driver_account(obj)
        sub = a["subscription"]
        level = a["level"]
        return {
            "level": level["level"],
            "level_name": level["name"],
            "next_level_name": level["next"]["name"] if level["next"] else None,
            "next_level_needs": level["needs"],
            "completed_trips": a["completed_trips"],
            "fares_total": str(a["fares_total"]),
            "earnings_total": str(a["earnings_total"]),
            "company_total": str(a["company_total"]),
            "paid_total": str(a["paid_total"]),
            "balance_due": str(a["balance_due"]),
            "subscription_status": a["subscription_status"],
            "subscription_ends_on": sub.ends_on.isoformat() if sub and sub.ends_on else None,
            "subscription_days_left": a["subscription_days_left"],
            "can_accept_trips": a["subscription_status"] != "expired",
        }


class DriverRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=80)
    middle_name = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=80)
    vehicle_type = serializers.IntegerField()
    vehicle_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    vehicle_color = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    license_plate = serializers.CharField(max_length=20)
    license_number = serializers.CharField(max_length=50)
    license_photo = serializers.ImageField()
    profile_photo = serializers.ImageField()
    region = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")

    def validate_license_plate(self, value):
        if not value:
            raise serializers.ValidationError("License plate number is required.")
        return value

    def validate_license_number(self, value):
        if not value:
            raise serializers.ValidationError("License number is required.")
        return value
