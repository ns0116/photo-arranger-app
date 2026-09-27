import io
import os
import shutil
import tempfile
from datetime import datetime

from PIL import Image
from PIL.ExifTags import IFD

from services.geocoding_service import (
    CITIES,
    format_gps_string,
    haversine_distance_km,
    reverse_geocode,
)
from services.photo_service import _arrange_photos_stream, parse_naming_template
from services.rule_service import evaluate_rules, resolve_rule_target_folder
from utils.date_utils import _dms_to_decimal, get_exif_validation


def create_gps_image(filepath, lat=None, lon=None, dt=None):
    """Creates a temporary test image with optional GPS and date EXIF tags."""
    img = Image.new("RGB", (30, 30), color="blue")
    exif = Image.Exif()

    if dt:
        exif[306] = dt.strftime("%Y:%m:%d %H:%M:%S")

    if lat is not None and lon is not None:
        lat_ref = "N" if lat >= 0 else "S"
        lon_ref = "E" if lon >= 0 else "W"
        abs_lat = abs(lat)
        abs_lon = abs(lon)

        lat_d = int(abs_lat)
        lat_m = int((abs_lat - lat_d) * 60)
        lat_s = round(((abs_lat - lat_d) * 60 - lat_m) * 60, 2)

        lon_d = int(abs_lon)
        lon_m = int((abs_lon - lon_d) * 60)
        lon_s = round(((abs_lon - lon_d) * 60 - lon_m) * 60, 2)

        exif[IFD.GPSInfo] = {
            1: lat_ref,
            2: (float(lat_d), float(lat_m), float(lat_s)),
            3: lon_ref,
            4: (float(lon_d), float(lon_m), float(lon_s)),
        }

    img.save(filepath, format="JPEG", exif=exif)


def test_haversine_distance():
    # Tokyo to Yokohama is approx 28 km
    d = haversine_distance_km(35.6895, 139.6917, 35.4437, 139.6380)
    assert 25 < d < 35

    # Same coordinates should return 0 km
    d_same = haversine_distance_km(35.6895, 139.6917, 35.6895, 139.6917)
    assert d_same == 0.0


def test_reverse_geocode_cities():
    # Tokyo
    loc = reverse_geocode(35.6895, 139.6917)
    assert loc["has_gps"] is True
    assert loc["city"] == "Tokyo"
    assert loc["city_ja"] == "東京"
    assert loc["country"] == "Japan"
    assert loc["country_ja"] == "日本"
    assert loc["distance_km"] < 1.0

    # Kyoto
    loc_kyoto = reverse_geocode(35.0116, 135.7681)
    assert loc_kyoto["city"] == "Kyoto"
    assert loc_kyoto["city_ja"] == "京都"

    # Paris
    loc_paris = reverse_geocode(48.8566, 2.3522)
    assert loc_paris["city"] == "Paris"
    assert loc_paris["city_ja"] == "パリ"
    assert loc_paris["country"] == "France"

    # Honolulu
    loc_hnl = reverse_geocode(21.3069, -157.8583)
    assert loc_hnl["city"] == "Honolulu"
    assert loc_hnl["country"] == "USA"

    # Sydney (Southern Hemisphere)
    loc_syd = reverse_geocode(-33.8688, 151.2093)
    assert loc_syd["city"] == "Sydney"
    assert loc_syd["country"] == "Australia"


def test_reverse_geocode_missing_or_none():
    loc = reverse_geocode(None, None)
    assert loc["has_gps"] is False
    assert loc["city"] == "No_Location"
    assert loc["city_ja"] == "位置情報なし"
    assert loc["country"] == "No_Location"
    assert loc["distance_km"] is None


def test_format_gps_string():
    assert format_gps_string(35.6895, 139.6917) == "35.69N_139.69E"
    assert format_gps_string(-33.8688, 151.2093) == "33.87S_151.21E"
    assert format_gps_string(40.7128, -74.0060) == "40.71N_74.01W"
    assert format_gps_string(None, None) == "No_GPS"


def test_dms_to_decimal():
    # 35 deg 30 min 0 sec N = 35.5
    assert _dms_to_decimal((35, 30, 0), "N") == 35.5
    # 35 deg 30 min 0 sec S = -35.5
    assert _dms_to_decimal((35, 30, 0), "S") == -35.5
    # 120 deg 15 min 0 sec W = -120.25
    assert _dms_to_decimal((120, 15, 0), "W") == -120.25
    # Invalid inputs
    assert _dms_to_decimal(None, "N") is None
    assert _dms_to_decimal((10,), "N") is None
    assert _dms_to_decimal(("bad", 1, 2), "N") is None


def test_get_exif_validation_with_gps():
    temp_dir = tempfile.mkdtemp()
    try:
        # 1. Image with GPS (Tokyo)
        img_gps = os.path.join(temp_dir, "tokyo.jpg")
        dt_val = datetime(2026, 7, 15, 14, 30, 0)
        create_gps_image(img_gps, lat=35.6895, lon=139.6917, dt=dt_val)

        val = get_exif_validation(img_gps)
        assert val["corrupt"] is False
        assert val["lat"] is not None
        assert abs(val["lat"] - 35.6895) < 0.01
        assert abs(val["lon"] - 139.6917) < 0.01
        assert val["location"]["has_gps"] is True
        assert val["location"]["city"] == "Tokyo"
        assert val["location"]["country"] == "Japan"

        # 2. Image without GPS
        img_nogps = os.path.join(temp_dir, "nogps.jpg")
        create_gps_image(img_nogps, dt=dt_val)
        val_nogps = get_exif_validation(img_nogps)
        assert val_nogps["lat"] is None
        assert val_nogps["lon"] is None
        assert val_nogps["location"]["has_gps"] is False
        assert val_nogps["location"]["city"] == "No_Location"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_parse_naming_template_with_location():
    dt = datetime(2026, 8, 20)
    loc = reverse_geocode(35.0116, 135.7681)  # Kyoto

    # English tokens
    res = parse_naming_template(
        "{country}/{city}/{YYYY-MM-DD}", dt, "temple.jpg", location=loc
    )
    assert res == "Japan/Kyoto/2026-08-20"

    # Japanese tokens
    res_ja = parse_naming_template(
        "{country_ja}/{city_ja}/{YYYY}/{filename}{ext}",
        dt,
        "temple.jpg",
        location=loc,
    )
    assert res_ja == "日本/京都/2026/temple.jpg"

    # GPS coordinates token
    res_gps = parse_naming_template(
        "{gps}/{filename}{ext}", dt, "temple.jpg", location=loc
    )
    assert "35.01N_135.77E/temple.jpg" == res_gps

    # Missing location fallback
    loc_empty = reverse_geocode(None, None)
    res_fallback = parse_naming_template(
        "{country}/{city}/{YYYY-MM-DD}", dt, "temple.jpg", location=loc_empty
    )
    assert res_fallback == "No_Location/No_Location/2026-08-20"


def test_rule_evaluation_with_location():
    dt = datetime(2026, 5, 10)
    loc_tokyo = reverse_geocode(35.6895, 139.6917)
    loc_paris = reverse_geocode(48.8566, 2.3522)
    loc_none = reverse_geocode(None, None)

    rules = [
        {
            "id": "r1",
            "field": "city",
            "operator": "equals",
            "value": "Tokyo",
            "target_folder": "Domestic/Tokyo/{YYYY}",
        },
        {
            "id": "r2",
            "field": "country",
            "operator": "contains",
            "value": "France",
            "target_folder": "Overseas/{country}/{city}",
        },
        {
            "id": "r3",
            "field": "has_gps",
            "operator": "equals",
            "value": "true",
            "target_folder": "Other_GPS/{gps}",
        },
    ]

    # File 1: Tokyo -> matches r1
    ctx_tokyo = {
        "filename": "tokyo.jpg",
        "extension": ".jpg",
        "dt": dt,
        "location": loc_tokyo,
    }
    folder, matched = evaluate_rules(rules, ctx_tokyo)
    assert folder == "Domestic/Tokyo/2026"
    assert matched["id"] == "r1"

    # File 2: Paris -> matches r2
    ctx_paris = {
        "filename": "paris.jpg",
        "extension": ".jpg",
        "dt": dt,
        "location": loc_paris,
    }
    folder_p, matched_p = evaluate_rules(rules, ctx_paris)
    assert folder_p == "Overseas/France/Paris"
    assert matched_p["id"] == "r2"

    # File 3: Honolulu -> matches r3 (has_gps=true)
    loc_hnl = reverse_geocode(21.3069, -157.8583)
    ctx_hnl = {
        "filename": "beach.jpg",
        "extension": ".jpg",
        "dt": dt,
        "location": loc_hnl,
    }
    folder_h, matched_h = evaluate_rules(rules, ctx_hnl)
    assert folder_h == "Other_GPS/21.31N_157.86W"
    assert matched_h["id"] == "r3"

    # File 4: No GPS -> none matched
    ctx_none = {
        "filename": "indoor.jpg",
        "extension": ".jpg",
        "dt": dt,
        "location": loc_none,
    }
    folder_none, matched_none = evaluate_rules(rules, ctx_none)
    assert folder_none is None
    assert matched_none is None


def test_arrange_photos_stream_with_location():
    temp_dir = tempfile.mkdtemp()
    src_dir = os.path.join(temp_dir, "src")
    dst_dir = os.path.join(temp_dir, "dst")
    os.makedirs(src_dir)
    os.makedirs(dst_dir)

    try:
        # Create 1 image with Tokyo GPS and 1 image without GPS
        create_gps_image(
            os.path.join(src_dir, "photo_tokyo.jpg"),
            lat=35.6895,
            lon=139.6917,
            dt=datetime(2026, 6, 1),
        )
        create_gps_image(
            os.path.join(src_dir, "photo_nogps.jpg"),
            dt=datetime(2026, 6, 2),
        )

        gen = _arrange_photos_stream(
            src_dirs=[src_dir],
            dst_dir=dst_dir,
            naming_rule="{country}/{city}/{YYYY-MM-DD}",
            mode="copy",
            dry_run=False,
        )
        chunks = list(gen)
        assert len(chunks) > 0

        # Verify destination files
        tokyo_dest = os.path.join(
            dst_dir, "Japan", "Tokyo", "2026-06-01", "photo_tokyo.jpg"
        )
        nogps_dest = os.path.join(
            dst_dir, "No_Location", "No_Location", "2026-06-02", "photo_nogps.jpg"
        )

        assert os.path.exists(tokyo_dest)
        assert os.path.exists(nogps_dest)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
