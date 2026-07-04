import os
from datetime import datetime

from utils.date_utils import get_exif_date


def test_valid_exif_date(temp_workspace, image_creator):
    """Test get_exif_date correctly extracts a valid EXIF date taken."""
    filepath = os.path.join(temp_workspace["src"], "valid_exif.jpg")
    image_creator(filepath, exif_date_str="2026:06:01 12:00:00")

    dt = get_exif_date(filepath)
    assert dt is not None
    assert dt == datetime(2026, 6, 1)


def test_no_exif_date(temp_workspace, image_creator):
    """Test get_exif_date returns None for an image without EXIF metadata."""
    filepath = os.path.join(temp_workspace["src"], "no_exif.jpg")
    image_creator(filepath)

    dt = get_exif_date(filepath)
    assert dt is None


def test_non_image_extension(temp_workspace, image_creator):
    """Test get_exif_date returns None immediately for non-image file extensions."""
    filepath = os.path.join(temp_workspace["src"], "document.txt")
    image_creator(filepath, content=b"plain text content")

    dt = get_exif_date(filepath)
    assert dt is None


def test_invalid_exif_date_format(temp_workspace, image_creator):
    """Test get_exif_date handles invalid date string formats gracefully."""
    filepath = os.path.join(temp_workspace["src"], "invalid_exif.jpg")
    image_creator(filepath, exif_date_str="invalid-date-string")

    dt = get_exif_date(filepath)
    assert dt is None
