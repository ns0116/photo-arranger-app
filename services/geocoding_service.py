import math

from services.cities_data import CITIES

__all__ = [
    "CITIES",
    "haversine_distance_km",
    "reverse_geocode",
    "format_gps_string",
]


def haversine_distance_km(lat1, lon1, lat2, lon2):
    """Calculates the great-circle distance between two points in km."""
    rad = math.pi / 180.0
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return 6371.0 * c


def reverse_geocode(lat, lon, max_distance_km=None):
    """Performs offline reverse geocoding to find the nearest city and country.

    Args:
        lat (float or None): Latitude in decimal degrees.
        lon (float or None): Longitude in decimal degrees.
        max_distance_km (float, optional): Maximum distance threshold in km.

    Returns:
        dict: Geocoded location information containing:
            - has_gps: bool
            - city: str (English city name or 'No_Location')
            - city_ja: str (Japanese city name or '位置情報なし')
            - country: str (English country name or 'No_Location')
            - country_ja: str (Japanese country name or '位置情報なし')
            - distance_km: float or None
            - lat: float or None
            - lon: float or None
    """
    if lat is None or lon is None:
        return {
            "has_gps": False,
            "city": "No_Location",
            "city_ja": "位置情報なし",
            "country": "No_Location",
            "country_ja": "位置情報なし",
            "distance_km": None,
            "lat": None,
            "lon": None,
        }

    rad = math.pi / 180.0
    lat_r = lat * rad
    lon_r = lon * rad

    best_dist_sq = float("inf")
    best_entry = None

    # Equirectangular approximation for rapid search
    for city_en, city_ja, country_en, country_ja, c_lat, c_lon in CITIES:
        c_lat_r = c_lat * rad
        c_lon_r = c_lon * rad
        x = (c_lon_r - lon_r) * math.cos((lat_r + c_lat_r) / 2.0)
        y = c_lat_r - lat_r
        d2 = x * x + y * y
        if d2 < best_dist_sq:
            best_dist_sq = d2
            best_entry = (city_en, city_ja, country_en, country_ja, c_lat, c_lon)

    if best_entry is None:
        return {
            "has_gps": True,
            "city": "Unknown_City",
            "city_ja": "不明な都市",
            "country": "Unknown_Country",
            "country_ja": "不明な国",
            "distance_km": None,
            "lat": lat,
            "lon": lon,
        }

    city_en, city_ja, country_en, country_ja, c_lat, c_lon = best_entry
    exact_km = round(haversine_distance_km(lat, lon, c_lat, c_lon), 1)

    if max_distance_km is not None and exact_km > max_distance_km:
        return {
            "has_gps": True,
            "city": "Unknown_City",
            "city_ja": "不明な都市",
            "country": country_en,
            "country_ja": country_ja,
            "distance_km": exact_km,
            "lat": lat,
            "lon": lon,
        }

    return {
        "has_gps": True,
        "city": city_en,
        "city_ja": city_ja,
        "country": country_en,
        "country_ja": country_ja,
        "distance_km": exact_km,
        "lat": lat,
        "lon": lon,
    }


def format_gps_string(lat, lon):
    """Formats decimal coordinates into a clean folder/tag string like '35.69N_139.69E'.

    Returns 'No_GPS' if coordinates are missing.
    """
    if lat is None or lon is None:
        return "No_GPS"

    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return f"{abs(lat):.2f}{lat_dir}_{abs(lon):.2f}{lon_dir}"
