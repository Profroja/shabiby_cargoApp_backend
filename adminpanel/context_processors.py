from django.conf import settings


def google_maps(request):
    """Expose the Google Maps browser key to admin templates."""
    return {"GOOGLE_MAPS_API_KEY": getattr(settings, "GOOGLE_MAPS_API_KEY", "")}
