"""OSM Nominatim geocoding — visit-radius verification, free, no key.

Division of labor (from the v2 spec): geocoding answers "is this address
within the drive radius" MECHANICALLY; agent/web checks are reserved for the
question geocoding can't answer — "is this a real facility or a sales
office." Never spend an agent on arithmetic.

Etiquette: Nominatim is a shared public service — max 1 req/s, identify
yourself via User-Agent. Bulk geocoding belongs on a self-hosted instance.
"""
import json
import math
import time
import urllib.parse
import urllib.request

from . import _net

UA = "gtm-system/1.0 (visit-radius verification)"


def geocode(address, timeout=20):
    q = urllib.parse.urlencode({"q": address, "format": "json", "limit": 1})
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{q}", headers={"User-Agent": UA}
    )
    with _net.urlopen(req, timeout=timeout) as r:
        rows = json.load(r)
    time.sleep(1.1)  # etiquette floor, not a tunable
    if not rows:
        return None
    return float(rows[0]["lat"]), float(rows[0]["lon"])


def haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def within_radius(addr_latlon, center_latlon, max_drive_min):
    """Straight-line proxy: ~55 km/h effective average → drive minutes.
    Deliberately conservative; borderline cases go to the human, not the bin.
    (Sonora/Yreka precedent: >2h straight-line got demoted to call, correctly.)"""
    km = haversine_km(addr_latlon, center_latlon)
    return (km / 55.0) * 60 <= max_drive_min
