import logging
import random
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import OTPCode

User = get_user_model()
logger = logging.getLogger(__name__)


def otp_expiry_minutes():
    return getattr(settings, "OTP_EXPIRY_MINUTES", 10)


def normalize_phone(value):
    """Store and match phones as local 0XXXXXXXXX, whatever format is sent."""
    digits = re.sub(r"\D", "", str(value))
    if digits.startswith("255") and len(digits) == 12:
        digits = "0" + digits[3:]
    elif len(digits) == 9:
        digits = "0" + digits
    return digits or str(value).strip()


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        return normalize_phone(value)

    def save(self):
        phone = self.validated_data["phone_number"]
        code = f"{random.randint(0, 999999):06d}"
        otp = OTPCode.objects.create(
            phone_number=phone,
            code=code,
            expires_at=timezone.now() + timezone.timedelta(minutes=otp_expiry_minutes()),
        )
        return otp


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)

    def validate_phone_number(self, value):
        return normalize_phone(value)

    def validate_code(self, value):
        return value.strip()

    def validate(self, attrs):
        phone = attrs.get("phone_number")
        code = attrs.get("code")
        now = timezone.now()

        matches = OTPCode.objects.filter(phone_number=phone, code=code)
        otp = matches.filter(is_used=False, expires_at__gt=now).order_by("-created_at").first()
        if otp:
            attrs["otp"] = otp
            return attrs

        # Work out why it failed so the user gets a useful message.
        latest_match = matches.order_by("-created_at").first()
        if latest_match is None:
            reason, message = "wrong_code", "Incorrect code. Check the SMS and try again."
        elif latest_match.is_used:
            reason, message = "used", "This code has already been used. Request a new code."
        else:
            reason, message = "expired", "This code has expired. Request a new code."

        logger.warning(
            "OTP verify failed for %s: %s (codes sent in last hour: %s)",
            phone,
            reason,
            OTPCode.objects.filter(
                phone_number=phone, created_at__gt=now - timezone.timedelta(hours=1)
            ).count(),
        )
        raise serializers.ValidationError(message)


class CompleteRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=80)
    middle_name = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=80)
    role = serializers.ChoiceField(
        choices=["customer", "driver"], default="customer"
    )


class GoogleLoginSerializer(serializers.Serializer):
    google_id_token = serializers.CharField()

    def validate_google_id_token(self, value):
        # In production, verify the Google ID token using google-auth library.
        # For now, we accept the token and decode it client-side or via google API.
        return value
