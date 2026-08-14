import random

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import OTPCode

User = get_user_model()


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        return value

    def save(self):
        phone = self.validated_data["phone_number"]
        code = f"{random.randint(0, 999999):06d}"
        otp = OTPCode.objects.create(
            phone_number=phone,
            code=code,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        return otp


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        phone = attrs.get("phone_number")
        code = attrs.get("code")

        otp = (
            OTPCode.objects.filter(
                phone_number=phone,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

        if not otp:
            raise serializers.ValidationError("Invalid or expired OTP code.")

        attrs["otp"] = otp
        return attrs


class CompleteRegistrationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    role = serializers.ChoiceField(
        choices=["customer", "driver"], default="customer"
    )

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value, first_name__gt="").exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value


class GoogleLoginSerializer(serializers.Serializer):
    google_id_token = serializers.CharField()

    def validate_google_id_token(self, value):
        # In production, verify the Google ID token using google-auth library.
        # For now, we accept the token and decode it client-side or via google API.
        return value
