from django.conf import settings


def panel_settings(request):
    """Settings shared by all admin templates: Google Maps key, default pricing."""
    return {
        "GOOGLE_MAPS_API_KEY": getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
        "default_price_per_km": getattr(settings, "DEFAULT_PRICE_PER_KM", 600),
    }
