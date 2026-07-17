import os
from datetime import datetime, timedelta

from PIL import Image
from PIL.ExifTags import TAGS

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


def get_exif_validation(filepath):
    """Inspects an image file for decode failures and EXIF date sanity.

    This is the single place that opens/decodes the image so callers needing
    both the resolved date and any corruption/abnormal-date warnings only pay
    the Pillow decode cost once (see issue #32).

    Returns a dict:
        {
            "dt": datetime | None,        # resolved EXIF date-taken, if any
            "corrupt": bool,               # True if Pillow could not decode the file
            "corrupt_detail": str | None,  # raw (untranslated) exception detail
            "abnormal_date": bool,         # True if dt is implausible
            "abnormal_reason": "future" | "too_old" | None,
        }
    """
    result = {
        "dt": None,
        "corrupt": False,
        "corrupt_detail": None,
        "abnormal_date": False,
        "abnormal_reason": None,
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
