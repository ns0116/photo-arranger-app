import os
from datetime import datetime, timedelta

from PIL import Image
from PIL.ExifTags import IFD, TAGS

from config import Config


def _extract_exif_datetime(img):
    """Reads the first usable date-taken tag from an already-opened Pillow image.

    Returns a datetime object if successfully parsed, or None otherwise.

    Only extensions in Config.IMAGE_EXTENSIONS are attempted. Video files
    (Config.VIDEO_EXTENSIONS) are intentionally excluded here since Pillow
    cannot read EXIF from them; callers fall back to file mtime for those,
    matching the existing fallback used for images without EXIF data.
    """
    exif_data = img.getexif()
    if not exif_data:
        return None
    for tag, value in exif_data.items():
        tag_name = TAGS.get(tag, tag)
        if tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
            if isinstance(value, str) and len(value) >= 10:
                # Standard format: "YYYY:MM:DD HH:MM:SS"
                date_str = value[:10].replace(":", "-")
                parts = date_str.split("-")
                if len(parts) == 3 and all(p.isdigit() for p in parts):
                    return datetime.strptime(date_str, "%Y-%m-%d")
    return None


def _extract_exif_camera_model(img):
    """Extracts the camera model string from EXIF data, or None if not present."""
    exif_data = img.getexif()
    if not exif_data:
        return None
    val = exif_data.get(0x0110)
    if val and isinstance(val, str):
        return val.strip()
    for tag, value in exif_data.items():
        if TAGS.get(tag, tag) == "Model" and isinstance(value, str):
            return value.strip()
    return None


def _dms_to_decimal(dms, ref):
    """Converts a (degrees, minutes, seconds) tuple or list to decimal degrees."""
    if not dms or len(dms) < 3:
        return None
    try:
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        dec = d + (m / 60.0) + (s / 3600.0)
        if str(ref).strip().upper() in ("S", "W"):
            dec = -dec
        return dec
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def _extract_exif_gps(img):
    """Extracts (latitude, longitude) as float tuple or (None, None) from Pillow Image."""
    try:
        exif = img.getexif()
        gps_ifd = None
        if exif:
            gps_ifd = exif.get_ifd(IFD.GPSInfo)
        if not gps_ifd and hasattr(img, "_getexif"):
            raw = img._getexif()
            if raw and 34853 in raw:
                gps_ifd = raw[34853]

        if not gps_ifd:
            return None, None

        lat_ref = gps_ifd.get(1) or gps_ifd.get("GPSLatitudeRef")
        lat_val = gps_ifd.get(2) or gps_ifd.get("GPSLatitude")
        lon_ref = gps_ifd.get(3) or gps_ifd.get("GPSLongitudeRef")
        lon_val = gps_ifd.get(4) or gps_ifd.get("GPSLongitude")

        lat = _dms_to_decimal(lat_val, lat_ref)
        lon = _dms_to_decimal(lon_val, lon_ref)
        if lat is not None and lon is not None:
            return round(lat, 6), round(lon, 6)
    except Exception:
        pass
    return None, None


def get_exif_validation(filepath, include_phash=False):
    """Inspects an image file for decode failures and EXIF date sanity.

    This is the single place that opens/decodes the image so callers needing
    both the resolved date and any corruption/abnormal-date warnings only pay
    the Pillow decode cost once (see issue #32).

    When include_phash=True, also computes the perceptual hash (dHash) for
    near-duplicate detection (see issue #25). The hash calculation is isolated
    so any failure never impacts corrupt/abnormal_date determination.

    Returns a dict:
        {
            "dt": datetime | None,        # resolved EXIF date-taken, if any
            "camera_model": str | None,   # EXIF camera model, if any
            "lat": float | None,          # GPS latitude
            "lon": float | None,          # GPS longitude
            "location": dict,             # geocoded location (city, country, etc.)
            "corrupt": bool,               # True if Pillow could not decode the file
            "corrupt_detail": str | None,  # raw (untranslated) exception detail
            "abnormal_date": bool,         # True if dt is implausible
            "abnormal_reason": "future" | "too_old" | None,
            "phash": str | None,           # 16-hex perceptual hash (if include_phash=True)
        }
    """
    from services.geocoding_service import reverse_geocode

    result = {
        "dt": None,
        "camera_model": None,
        "lat": None,
        "lon": None,
        "location": reverse_geocode(None, None),
        "corrupt": False,
        "corrupt_detail": None,
        "abnormal_date": False,
        "abnormal_reason": None,
        "phash": None,
    }

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in Config.IMAGE_EXTENSIONS:
        return result

    try:
        with Image.open(filepath) as img:
            # Force a full pixel decode (Image.open only parses the header/
            # metadata lazily), so truncated/corrupt image data is caught here
            # rather than surfacing later during processing.
            img.load()
            result["dt"] = _extract_exif_datetime(img)
            result["camera_model"] = _extract_exif_camera_model(img)
            lat, lon = _extract_exif_gps(img)
            result["lat"] = lat
            result["lon"] = lon
            result["location"] = reverse_geocode(lat, lon)

            if include_phash:
                try:
                    from utils.phash_utils import compute_phash

                    result["phash"] = compute_phash(img)
                except Exception:
                    result["phash"] = None
    except Exception as e:
        result["corrupt"] = True
        result["corrupt_detail"] = str(e)
        return result

    dt = result["dt"]
    if dt is not None:
        future_cutoff = datetime.now() + timedelta(
            minutes=Config.EXIF_FUTURE_TOLERANCE_MINUTES
        )
        if dt > future_cutoff:
            result["abnormal_date"] = True
            result["abnormal_reason"] = "future"
        elif dt < Config.EXIF_MIN_VALID_DATE:
            result["abnormal_date"] = True
            result["abnormal_reason"] = "too_old"

    return result


def get_exif_date(filepath):
    """Extract EXIF Date Taken from an image file using Pillow.

    Returns a datetime object if successfully parsed, or None otherwise
    (including when the file is unreadable/corrupt). Kept as a light wrapper
    around get_exif_validation() for callers that only need the date, such as
    the date-range scan filter.
    """
    return get_exif_validation(filepath)["dt"]
