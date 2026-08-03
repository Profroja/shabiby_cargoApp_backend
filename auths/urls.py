from django.urls import path

from .views import (
    CompleteRegistrationView,
    GoogleLoginView,
    MeView,
    SendOTPView,
    VerifyOTPView,
)

urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("register/", CompleteRegistrationView.as_view(), name="complete-registration"),
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    path("me/", MeView.as_view(), name="me"),
]
