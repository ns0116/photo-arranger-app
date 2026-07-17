import os
from datetime import datetime
from unittest.mock import patch

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


def test_video_extension_returns_none(temp_workspace, image_creator):
    """Test get_exif_date returns None for video files (not an error, no EXIF support)."""
    filepath = os.path.join(temp_workspace["src"], "clip.mp4")
    image_creator(filepath, content=b"not a real mp4, just plain bytes")

    dt = get_exif_date(filepath)
    assert dt is None


def test_video_extension_does_not_invoke_pillow(temp_workspace, image_creator):
    """Test get_exif_date skips Pillow entirely for video extensions.

    Video files aren't valid images, so calling Image.open on them would raise.
    This confirms the extension guard short-circuits before Pillow is ever touched,
    for every extension in Config.VIDEO_EXTENSIONS.
    """
    from config import Config

    for ext in Config.VIDEO_EXTENSIONS:
        filepath = os.path.join(temp_workspace["src"], f"clip{ext}")
        image_creator(filepath, content=b"not a real video, just plain bytes")

        with patch("utils.date_utils.Image.open") as mock_open:
            dt = get_exif_date(filepath)

        assert dt is None
        mock_open.assert_not_called()
