import json
import os
import threading
from datetime import datetime

import pytest

from services.photo_service import arrange_photos, process_file_task, scan_directories


def test_scan_directories(temp_workspace, image_creator):
    """Test scan_directories scans correct files and excludes hidden files."""
    src = temp_workspace["src"]
    image_creator(os.path.join(src, "photo1.jpg"))
    image_creator(os.path.join(src, ".hidden_photo.jpg"))
    image_creator(os.path.join(src, "photo2.png"))
    os.mkdir(os.path.join(src, "subdir"))

    files = scan_directories([src])
    filenames = [f[1] for f in files]
    assert len(filenames) == 2
    assert "photo1.jpg" in filenames
    assert "photo2.png" in filenames
    assert ".hidden_photo.jpg" not in filenames
    assert "subdir" not in filenames


def test_scan_directories_includes_video_files(temp_workspace, image_creator):
    """Test scan_directories includes video extensions by default, alongside images."""
    src = temp_workspace["src"]
    image_creator(os.path.join(src, "photo1.jpg"))
    image_creator(os.path.join(src, "clip.mp4"), content=b"fake mp4 data")
    image_creator(os.path.join(src, "movie.mov"), content=b"fake mov data")
    image_creator(os.path.join(src, "notes.txt"), content=b"plain text content")

    files = scan_directories([src])
    filenames = [f[1] for f in files]
    assert "photo1.jpg" in filenames
    assert "clip.mp4" in filenames
    assert "movie.mov" in filenames
    assert "notes.txt" not in filenames


def test_scan_directories_extension_filter_video_only(temp_workspace, image_creator):
    """Test the extensions filter can restrict scanning to only the selected video type."""
    src = temp_workspace["src"]
    image_creator(os.path.join(src, "photo1.jpg"))
    image_creator(os.path.join(src, "clip.mp4"), content=b"fake mp4 data")
    image_creator(os.path.join(src, "movie.mov"), content=b"fake mov data")

    files = scan_directories([src], extensions=[".mp4"])
    filenames = [f[1] for f in files]
    assert filenames == ["clip.mp4"]


def test_process_file_task_video_uses_mtime_fallback(temp_workspace, image_creator):
    """Test process_file_task resolves video files via mtime since EXIF is unavailable."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    filepath = os.path.join(src, "clip.mp4")
    image_creator(filepath, content=b"fake mp4 data")

    # Pin mtime to a known date so the resulting folder name is deterministic.
    target_ts = datetime(2026, 3, 15, 10, 0, 0).timestamp()
    os.utime(filepath, (target_ts, target_ts))

    cancel_ev = threading.Event()
    res = process_file_task(src, "clip.mp4", dst, "%Y-%m-%d", "copy", True, cancel_ev)

    assert res["status"] == "success"
    assert res["action"] == "copy"
    assert res["folder"] == "2026-03-15"


def test_process_file_task_dry_run_copy(temp_workspace, image_creator):
    """Test process_file_task simulates copy without writing to disk."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    image_creator(os.path.join(src, "photo.jpg"), exif_date_str="2026:06:01 12:00:00")

    cancel_ev = threading.Event()
    res = process_file_task(src, "photo.jpg", dst, "%Y-%m-%d", "copy", True, cancel_ev)

    assert res["status"] == "success"
    assert res["action"] == "copy"
    assert res["folder"] == "2026-06-01"
    assert "新規コピー" in res["message"]
    assert not os.path.exists(os.path.join(dst, "2026-06-01", "photo.jpg"))


def test_process_file_task_dry_run_includes_full_path(temp_workspace, image_creator):
    """Test process_file_task dry-run result exposes the absolute source path.

    The frontend needs this to request a thumbnail preview (Issue #24) since the
    displayed 'src_dir' field is only the basename of the source directory.
    """
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    filepath = os.path.join(src, "photo.jpg")
    image_creator(filepath, exif_date_str="2026:06:01 12:00:00")

    cancel_ev = threading.Event()
    res = process_file_task(src, "photo.jpg", dst, "%Y-%m-%d", "copy", True, cancel_ev)

    assert res["full_path"] == filepath
    assert res["src_dir_full"] == src


def test_process_file_task_dry_run_move(temp_workspace, image_creator):
    """Test process_file_task simulates move without modifying files."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    image_creator(os.path.join(src, "photo.jpg"), exif_date_str="2026:06:01 12:00:00")

    cancel_ev = threading.Event()
    res = process_file_task(src, "photo.jpg", dst, "%Y-%m-%d", "move", True, cancel_ev)

    assert res["status"] == "success"
    assert res["action"] == "move"
    assert "新規移動" in res["message"]
    assert not os.path.exists(os.path.join(dst, "2026-06-01", "photo.jpg"))


def test_process_file_task_actual_copy(temp_workspace, image_creator):
    """Test process_file_task performs actual file copying."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    filepath = os.path.join(src, "photo.jpg")
    image_creator(filepath, exif_date_str="2026:06:01 12:00:00")

    cancel_ev = threading.Event()
    res = process_file_task(src, "photo.jpg", dst, "%Y-%m-%d", "copy", False, cancel_ev)

    assert res["status"] == "success"
    assert res["action"] == "copy"
    assert res["copied"] is True
    assert os.path.exists(os.path.join(dst, "2026-06-01", "photo.jpg"))
    assert os.path.exists(filepath)


def test_process_file_task_actual_move(temp_workspace, image_creator):
    """Test process_file_task performs actual file moving and deletes source."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    filepath = os.path.join(src, "photo.jpg")
    image_creator(filepath, exif_date_str="2026:06:01 12:00:00")

    cancel_ev = threading.Event()
    res = process_file_task(src, "photo.jpg", dst, "%Y-%m-%d", "move", False, cancel_ev)

    assert res["status"] == "success"
    assert res["action"] == "move"
    assert res["copied"] is True
    assert os.path.exists(os.path.join(dst, "2026-06-01", "photo.jpg"))
    assert not os.path.exists(filepath)


def test_process_file_task_cancelled(temp_workspace):
    """Test process_file_task exits early when cancellation is signaled."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    cancel_ev = threading.Event()
    cancel_ev.set()

    res = process_file_task(src, "photo.jpg", dst, "%Y-%m-%d", "copy", False, cancel_ev)
    assert res["status"] == "cancelled"


def test_process_file_task_exception_handling(temp_workspace):
    """Test process_file_task handles processing errors gracefully."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    cancel_ev = threading.Event()

    res = process_file_task(
        src, "non_existent.jpg", dst, "%Y-%m-%d", "copy", False, cancel_ev
    )
    assert res["status"] == "error"
    assert "エラー" in res["message"]


def test_process_file_task_flags_corrupt_file(temp_workspace, image_creator):
    """A corrupt/undecodable image is still processed (using the mtime fallback)
    but the result carries a 'corrupt' warning for the Dry Run preview (#32)."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    image_creator(os.path.join(src, "corrupt.jpg"), content=b"not a valid jpeg at all")

    cancel_ev = threading.Event()
    res = process_file_task(
        src, "corrupt.jpg", dst, "%Y-%m-%d", "copy", True, cancel_ev
    )

    assert res["status"] == "success"
    assert res["action"] == "copy"
    assert res["warning"] is not None
    assert res["warning"]["type"] == "corrupt"


def test_process_file_task_flags_future_exif_date(temp_workspace, image_creator):
    """A valid image whose EXIF date is in the future is flagged, but still
    processed normally into the (future-dated) folder."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    image_creator(os.path.join(src, "future.jpg"), exif_date_str="2099:01:01 12:00:00")

    cancel_ev = threading.Event()
    res = process_file_task(src, "future.jpg", dst, "%Y-%m-%d", "copy", True, cancel_ev)

    assert res["status"] == "success"
    assert res["folder"] == "2099-01-01"
    assert res["warning"] is not None
    assert res["warning"]["type"] == "abnormal_date"


def test_process_file_task_flags_epoch_exif_date(temp_workspace, image_creator):
    """A valid image with the classic epoch (1970-01-01) EXIF bug is flagged."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    image_creator(os.path.join(src, "epoch.jpg"), exif_date_str="1970:01:01 00:00:00")

    cancel_ev = threading.Event()
    res = process_file_task(src, "epoch.jpg", dst, "%Y-%m-%d", "copy", True, cancel_ev)

    assert res["status"] == "success"
    assert res["warning"] is not None
    assert res["warning"]["type"] == "abnormal_date"


def test_process_file_task_no_warning_for_normal_file(temp_workspace, image_creator):
    """A normal, valid image with a plausible EXIF date must not be flagged."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    image_creator(os.path.join(src, "photo.jpg"), exif_date_str="2026:06:01 12:00:00")

    cancel_ev = threading.Event()
    res = process_file_task(src, "photo.jpg", dst, "%Y-%m-%d", "copy", True, cancel_ev)

    assert res["status"] == "success"
    assert res["warning"] is None


def test_process_file_task_actual_run_copies_corrupt_file(
    temp_workspace, image_creator
):
    """Corrupt files are not silently dropped: the actual (non-dry-run) copy
    still succeeds, with the warning surfaced alongside the result."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    filepath = os.path.join(src, "corrupt.jpg")
    image_creator(filepath, content=b"not a valid jpeg at all")

    cancel_ev = threading.Event()
    res = process_file_task(
        src, "corrupt.jpg", dst, "%Y-%m-%d", "copy", False, cancel_ev
    )

    assert res["status"] == "success"
    assert res["copied"] is True
    assert res["warning"] is not None
    assert res["warning"]["type"] == "corrupt"
    # The file physically exists at the mtime-based fallback destination.
    assert os.path.exists(os.path.join(dst, res["folder"], "corrupt.jpg"))


def test_arrange_photos_pipeline_integration(temp_workspace, image_creator):
    """Test arrange_photos runs end-to-end and streams proper SSE JSON objects."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    image_creator(os.path.join(src, "photo1.jpg"), exif_date_str="2026:06:01 12:00:00")
    image_creator(os.path.join(src, "photo2.jpg"), exif_date_str="2026:06:02 12:00:00")

    generator = arrange_photos(
        [src], dst, naming_rule="YYYY-MM-DD", mode="copy", dry_run=False
    )
    results = list(generator)

    assert len(results) > 0
    last_chunk = results[-1]
    assert "completed" in last_chunk

    # Verify outputs placed in correct folders
    assert os.path.exists(os.path.join(dst, "2026-06-01", "photo1.jpg"))
    assert os.path.exists(os.path.join(dst, "2026-06-02", "photo2.jpg"))
