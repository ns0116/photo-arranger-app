import os
from datetime import datetime, timedelta

from utils.date_utils import get_exif_date, get_exif_validation


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


# --- get_exif_validation: corrupt file / abnormal date pre-flight checks (#32) ---


def test_validation_normal_image_not_flagged(temp_workspace, image_creator):
    """A well-formed image with a plausible EXIF date should never be flagged."""
    filepath = os.path.join(temp_workspace["src"], "normal.jpg")
    image_creator(filepath, exif_date_str="2026:06:01 12:00:00")

    result = get_exif_validation(filepath)
    assert result["dt"] == datetime(2026, 6, 1)
    assert result["corrupt"] is False
    assert result["abnormal_date"] is False
    assert result["abnormal_reason"] is None


def test_validation_no_exif_image_not_flagged(temp_workspace, image_creator):
    """A valid image with no EXIF date at all is not corrupt nor abnormal."""
    filepath = os.path.join(temp_workspace["src"], "no_exif.jpg")
    image_creator(filepath)

    result = get_exif_validation(filepath)
    assert result["dt"] is None
    assert result["corrupt"] is False
    assert result["abnormal_date"] is False


def test_validation_garbage_file_flagged_corrupt(temp_workspace, image_creator):
    """A file with an image extension but non-image bytes is detected as corrupt."""
    filepath = os.path.join(temp_workspace["src"], "corrupt.jpg")
    image_creator(filepath, content=b"this is definitely not a valid jpeg payload")

    result = get_exif_validation(filepath)
    assert result["corrupt"] is True
    assert result["corrupt_detail"]
    assert result["dt"] is None


def test_validation_truncated_image_flagged_corrupt(temp_workspace, image_creator):
    """A structurally-valid-but-truncated JPEG fails full pixel decode and is flagged.

    This exercises the img.load() call specifically (Image.open alone only
    parses headers lazily and would not catch this).
    """
    filepath = os.path.join(temp_workspace["src"], "truncated.jpg")
    image_creator(filepath, exif_date_str="2026:06:01 12:00:00")

    with open(filepath, "rb") as f:
        data = f.read()
    # Chop off the back half of the file to corrupt the pixel data while
    # leaving enough of the header for Image.open() to still succeed.
    with open(filepath, "wb") as f:
        f.write(data[: len(data) // 2])

    result = get_exif_validation(filepath)
    assert result["corrupt"] is True


def test_validation_future_date_flagged(temp_workspace, image_creator):
    """An EXIF date far in the future is flagged as abnormal."""
    filepath = os.path.join(temp_workspace["src"], "future.jpg")
    future_year = (datetime.now() + timedelta(days=365 * 5)).strftime("%Y")
    image_creator(filepath, exif_date_str=f"{future_year}:01:01 00:00:00")

    result = get_exif_validation(filepath)
    assert result["abnormal_date"] is True
    assert result["abnormal_reason"] == "future"
    assert result["corrupt"] is False


def test_validation_epoch_date_flagged(temp_workspace, image_creator):
    """The classic epoch (1970-01-01) EXIF bug is flagged as abnormally old."""
    filepath = os.path.join(temp_workspace["src"], "epoch.jpg")
    image_creator(filepath, exif_date_str="1970:01:01 00:00:00")

    result = get_exif_validation(filepath)
    assert result["abnormal_date"] is True
    assert result["abnormal_reason"] == "too_old"


def test_validation_pre_1980_date_flagged(temp_workspace, image_creator):
    """Dates before the configured threshold (1980) are flagged as abnormally old."""
    filepath = os.path.join(temp_workspace["src"], "old.jpg")
    image_creator(filepath, exif_date_str="1975:05:05 00:00:00")

    result = get_exif_validation(filepath)
    assert result["abnormal_date"] is True
    assert result["abnormal_reason"] == "too_old"


def test_get_exif_date_returns_none_for_corrupt_file(temp_workspace, image_creator):
    """The lightweight get_exif_date() wrapper stays backward compatible: corrupt
    files simply resolve to None (falling back to mtime), same as before."""
    filepath = os.path.join(temp_workspace["src"], "corrupt2.jpg")
    image_creator(filepath, content=b"not an image")

    assert get_exif_date(filepath) is None
