import json

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPCode
from .serializers import (
    CompleteRegistrationSerializer,
    GoogleLoginSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
)
from .sms_notification import send_sms_notification

User = get_user_model()


def _jwt_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.save()

        phone = serializer.validated_data["phone_number"]
        message = f"Your Shabiby Cargo verification code is: {otp.code}"

        sms_sent = send_sms_notification(phone, message)

        response_data = {
            "message": "OTP sent successfully.",
            "expires_in_minutes": 5,
        }

        if not sms_sent:
            response_data["message"] = "OTP generated but SMS delivery failed."
            response_data["sms_error"] = True

        return Response(response_data, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    Verify OTP. If the phone number belongs to an existing, fully-registered
    user, return JWT tokens immediately. If the user is new or hasn't completed
    registration (no first_name), return a session token so the client can
    call /api/auth/register/ to finish setup.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data["otp"]

        phone = serializer.validated_data["phone_number"]

        # Mark OTP as used
        otp.is_used = True
        otp.save(update_fields=["is_used"])

        user = User.objects.filter(phone_number=phone).first()

        if user and user.first_name:
            # Existing, fully-registered user → return JWT
            tokens = _jwt_for_user(user)
            return Response(
                {
                    "message": "Login successful.",
                    "is_new_user": False,
                    "tokens": tokens,
                    "user": {
                        "id": str(user.id),
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "phone_number": user.phone_number,
                        "role": user.role,
                    },
                },
                status=status.HTTP_200_OK,
            )

        # New or incomplete user → create a bare user and return a temp token
        if not user:
            username = f"phone_{phone}"
            user = User.objects.create_user(
                username=username,
                phone_number=phone,
                auth_provider="phone",
                is_phone_verified=True,
            )
        else:
            user.is_phone_verified = True
            user.save(update_fields=["is_phone_verified"])

        # Return a short-lived temp token (still JWT, but client must
        # call /api/auth/register/ to complete and get a fresh one)
        tokens = _jwt_for_user(user)
        return Response(
            {
                "message": "Phone verified. Please complete registration.",
                "is_new_user": True,
                "temp_tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class CompleteRegistrationView(APIView):
    """
    Step 2 for new phone users: provide first_name + last_name.
    Requires the temp JWT from VerifyOTP.
    """

    def post(self, request):
        serializer = CompleteRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.is_authenticated:
            return Response(
                {"error": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user.first_name = serializer.validated_data["first_name"]
        user.middle_name = serializer.validated_data.get("middle_name", "")
        user.last_name = serializer.validated_data["last_name"]
        role = serializer.validated_data.get("role", "customer")
        user.role = role
        user.save(update_fields=["first_name", "middle_name", "last_name", "role"])

        # Send SMS notification to the user
        full_name = f"{user.first_name} {user.last_name}".strip()
        sms_message = f"Karibu Shabiby Cargo, {full_name}! Akaunti yako imeundwa kwa mafanikio. Unaweza sasa kutuma na kufuatilia mizigo yako."
        sms_sent = send_sms_notification(user.phone_number, sms_message)

        # Issue fresh tokens
        tokens = _jwt_for_user(user)
        response_data = {
            "message": "Registration complete.",
            "registration_status": "success",
            "sms_notification_sent": sms_sent,
            "tokens": tokens,
            "user": {
                "id": str(user.id),
                "first_name": user.first_name,
                "middle_name": user.middle_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "role": user.role,
            },
        }
        return Response(response_data, status=status.HTTP_200_OK)


class GoogleLoginView(APIView):
    """
    Google login. Accepts a Google ID token, verifies it (in production),
    and returns JWT tokens. If the user doesn't exist, creates one using
    the Google profile info (name, email).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        google_id_token = serializer.validated_data["google_id_token"]

        # --- DEV MODE: decode the Google ID token payload without verification ---
        # In production, use: from google.auth.transport import requests
        #                      from google.oauth2 import id_token
        #                      info = id_token.verify_oauth2_token(google_id_token, requests.Request())
        try:
            payload_b64 = google_id_token.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(
                __import__("base64").urlsafe_b64decode(payload_b64).decode()
            )
        except Exception:
            return Response(
                {"error": "Invalid Google ID token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        google_id = payload.get("sub")
        email = payload.get("email")
        first_name = payload.get("given_name", "")
        last_name = payload.get("family_name", "")

        if not google_id:
            return Response(
                {"error": "Invalid Google token: missing user ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(google_id=google_id).first()
        if not user and email:
            user = User.objects.filter(email=email).first()
            if user:
                user.google_id = google_id
                user.auth_provider = "google"
                user.save(update_fields=["google_id", "auth_provider"])

        if not user:
            username = f"google_{google_id}"
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                google_id=google_id,
                auth_provider="google",
                is_phone_verified=False,
            )
        else:
            # Update name if user was created before without it
            if not user.first_name and first_name:
                user.first_name = first_name
                user.last_name = last_name
                user.save(update_fields=["first_name", "last_name"])

        tokens = _jwt_for_user(user)
        is_new = not bool(user.first_name)

        return Response(
            {
                "message": "Google login successful.",
                "is_new_user": is_new,
                "tokens": tokens,
                "user": {
                    "id": str(user.id),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone_number": user.phone_number,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """
    Get current user profile.
    """

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": str(user.id),
                "first_name": user.first_name,
                "middle_name": user.middle_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "email": user.email,
                "auth_provider": user.auth_provider,
                "role": user.role,
                "is_phone_verified": user.is_phone_verified,
            }
        )
