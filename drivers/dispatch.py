"""Which pickup requests a driver receives: those at the cargo station they
registered with (or that an admin assigned them to)."""
from django.core.exceptions import ValidationError


def local_station(station_id):
    """The admin-managed CargoStation with this id, or None (unknown or old main-system id)."""
    from stations.models import CargoStation

    if not station_id:
        return None
    try:
        return CargoStation.objects.filter(pk=station_id).first()
    except (ValidationError, ValueError):
        return None


def driver_station_ids(driver):
    """Station ids, as stored on trips, whose requests this driver should get.

    That is the driver's own station plus any station with the same name, so
    trips created against the old main-system station list still reach them.
    Drivers registered before stations were linked only have the station name
    (region) saved; that name is used instead. No station = no requests.
    """
    from stations.views import _get_center_map

    if driver.station_id:
        name = driver.station.name
        ids = {str(driver.station_id)}
    else:
        name = driver.region
        ids = set()
    name = (name or "").strip().lower()
    if name:
        for station_id, center in _get_center_map().items():
            if (center.get("center_name") or center.get("name") or "").strip().lower() == name:
                ids.add(str(station_id))
    return ids
