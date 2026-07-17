import os
from datetime import datetime

from PIL import Image
from PIL.ExifTags import TAGS

from config import Config


def get_exif_date(filepath):
    """Extract EXIF Date Taken from an image file using Pillow.

    Returns a datetime object if successfully parsed, or None otherwise.

    Only extensions in Config.IMAGE_EXTENSIONS are attempted. Video files
    (Config.VIDEO_EXTENSIONS) are intentionally excluded here since Pillow
    cannot read EXIF from them; callers fall back to file mtime for those,
    matching the existing fallback used for images without EXIF data.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in Config.IMAGE_EXTENSIONS:
        return None
    try:
        with Image.open(filepath) as img:
            exif_data = img.getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag, tag)
                    if tag_name in (
                        "DateTimeOriginal",
                        "DateTimeDigitized",
                        "DateTime",
                    ):
                        if isinstance(value, str) and len(value) >= 10:
                            # Standard format: "YYYY:MM:DD HH:MM:SS"
                            date_str = value[:10].replace(":", "-")
                            parts = date_str.split("-")
                            if len(parts) == 3 and all(p.isdigit() for p in parts):
                                return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        pass
    return None
