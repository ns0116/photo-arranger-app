import os
from datetime import datetime

import pytest

from config import Config
from services.photo_service import (
    parse_naming_template,
    process_file_task,
    scan_directories,
)
from utils.i18n import get_txt


def test_scan_directories_extension_filter(tmp_path):
    """Checks that directories are scanned and filtered by extensions correctly."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create test files
    (src_dir / "photo1.jpg").write_bytes(b"data1")
    (src_dir / "photo2.png").write_bytes(b"data2")
    (src_dir / "doc1.txt").write_bytes(b"text1")

    # Filter only JPG
    files = scan_directories([str(src_dir)], extensions=[".jpg"])
    assert len(files) == 1
    assert files[0][1] == "photo1.jpg"

    # Filter JPG & PNG
    files_both = scan_directories([str(src_dir)], extensions=[".jpg", ".png"])
    assert len(files_both) == 2
    filenames = [f[1] for f in files_both]
    assert "photo1.jpg" in filenames
    assert "photo2.png" in filenames


def test_scan_directories_date_filter(tmp_path):
    """Verifies that files are filtered by date range during directories scanning."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file1 = src_dir / "photo1.jpg"
    file2 = src_dir / "photo2.jpg"
    file1.write_bytes(b"data1")
    file2.write_bytes(b"data2")

    # Modify mtimes
    # Set file1 to 2026-01-01
    dt1 = datetime(2026, 1, 1).timestamp()
    os.utime(str(file1), (dt1, dt1))

    # Set file2 to 2026-06-01
    dt2 = datetime(2026, 6, 1).timestamp()
    os.utime(str(file2), (dt2, dt2))

    # Filter 2026-05-01 to 2026-07-01
    files = scan_directories(
        [str(src_dir)],
        extensions=[".jpg"],
        date_start="2026-05-01",
        date_end="2026-07-01",
    )
    assert len(files) == 1
    assert files[0][1] == "photo2.jpg"


def test_parse_naming_template():
    """Tests the resolution of placeholders in custom naming templates."""
    dt = datetime(2026, 6, 1)

    # Custom structure with filename and extension
    resolved = parse_naming_template(
        "{YYYY}/{MM}/{YYYY}-{MM}-{DD}_{filename}{ext}", dt, "vacation.png"
    )
    assert resolved == "2026/06/2026-06-01_vacation.png"

    # Simple folder template
    folder = parse_naming_template("{YYYY}-{MM}-{DD}", dt, "vacation.png")
    assert folder == "2026-06-01"


def test_custom_template_dry_run(tmp_path):
    """Verifies dry run execution when using a custom naming template."""
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    test_file = src_dir / "photo.jpg"
    test_file.write_bytes(b"data")
    dt = datetime(2026, 6, 1).timestamp()
    os.utime(str(test_file), (dt, dt))

    import threading

    cancel_event = threading.Event()

    # Execute file processing task simulation with a custom template
    res = process_file_task(
        s_dir=str(src_dir),
        filename="photo.jpg",
        dst_dir=str(dst_dir),
        naming_rule="{YYYY}/{MM}/{YYYY}-{MM}-{DD}_{filename}{ext}",
        mode="copy",
        dry_run=True,
        local_cancel_event=cancel_event,
        lang="ja",
    )

    assert res["status"] == "success"
    assert res["action"] == "copy"
    assert res["folder"] == "2026/06"
    assert res["target"] == "2026-06-01_photo.jpg"


def test_backend_translations():
    """Verifies that the translations helper functions resolve expected localized text keys."""
    # Test Japanese
    msg_ja = get_txt("ja", "user_cancelled")
    assert msg_ja == "ユーザーによって処理がキャンセルされました。"

    # Test English
    msg_en = get_txt("en", "user_cancelled")
    assert msg_en == "Operation cancelled by user."

    # Test format arguments
    msg_fmt = get_txt("en", "done_arrange", total=10, copied=8, skipped=1, errors=1)
    assert "Total 10" in msg_fmt
    assert "Success: 8" in msg_fmt
