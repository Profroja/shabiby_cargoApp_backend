from rest_framework import serializers

from .models import Driver


class DriverProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    vehicle_type_name = serializers.CharField(source="vehicle_type.display_name", read_only=True, default="")
    license_photo_url = serializers.SerializerMethodField()
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = (
            "id",
            "first_name",
            "last_name",
            "phone_number",
            "vehicle_type",
            "vehicle_type_name",
            "license_plate",
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

    def get_license_photo_url(self, obj):
        if obj.license_photo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.license_photo.url)
            return obj.license_photo.url
        return None

    def get_profile_photo_url(self, obj):
        if obj.profile_photo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.profile_photo.url)
            return obj.profile_photo.url
        return None


class DriverRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = (
            "vehicle_type",
            "license_plate",
            "national_id_number",
            "license_photo",
            "profile_photo",
        )

    def validate_license_plate(self, value):
        if not value:
            raise serializers.ValidationError("License plate is required.")
        return value

    def validate_national_id_number(self, value):
        if not value:
            raise serializers.ValidationError("Driver license ID is required.")
        return value
