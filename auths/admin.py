from django.contrib import admin

from .models import OTPCode


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "code", "is_used", "created_at", "expires_at")
    list_filter = ("is_used",)
    search_fields = ("phone_number",)
    ordering = ("-created_at",)
    readonly_fields = ("phone_number", "code", "is_used", "created_at", "expires_at")
