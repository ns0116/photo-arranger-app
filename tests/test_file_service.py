import hashlib
import os
import time
from unittest.mock import patch

import pytest

from config import Config
from services.file_service import (
    _stream_copy,
    are_files_identical_optimized,
    calculate_sha256,
    get_non_conflicting_path,
    safe_copy,
    safe_move,
)


def test_calculate_sha256(temp_workspace, image_creator):
    """Test calculate_sha256 correctly calculates SHA-256 hash."""
    filepath = os.path.join(temp_workspace["src"], "hash_test.txt")
    content = b"PhotoArrangerSHA256Test"
    image_creator(filepath, content=content)

    expected_hash = hashlib.sha256(content).hexdigest()
    assert calculate_sha256(filepath) == expected_hash


def test_safe_copy_success(temp_workspace, image_creator):
    """Test safe_copy successfully copies file and returns sha256 hash."""
    src = os.path.join(temp_workspace["src"], "source.jpg")
    dst = os.path.join(temp_workspace["dst"], "dest.jpg")
    content = b"ImageBytesContent"
    image_creator(src, content=content)

    result = safe_copy(src, dst)
    assert result  # truthy sha256 string
    assert os.path.exists(dst)
    with open(dst, "rb") as f:
        assert f.read() == content


def test_safe_copy_stream_error(temp_workspace, image_creator):
    """Test safe_copy raises IOError and cleans up target on stream-copy failure."""
    src = os.path.join(temp_workspace["src"], "source.jpg")
    dst = os.path.join(temp_workspace["dst"], "dest.jpg")
    image_creator(src, content=b"content-a")

    with patch("services.file_service._stream_copy", side_effect=IOError("disk full")):
        with pytest.raises(IOError):
            safe_copy(src, dst)

    # Destination file should be cleaned up (deleted)
    assert not os.path.exists(dst)


def test_safe_move_success(temp_workspace, image_creator):
    """Test safe_move successfully moves file and returns sha256 hash."""
    src = os.path.join(temp_workspace["src"], "source.jpg")
    dst = os.path.join(temp_workspace["dst"], "dest.jpg")
    content = b"ImageBytesContent"
    image_creator(src, content=content)

    result = safe_move(src, dst)
    assert result  # truthy sha256 string
    assert os.path.exists(dst)
    assert not os.path.exists(src)


def test_safe_move_failure(temp_workspace, image_creator):
    """Test safe_move retains source file if stream-copy fails on cross-device move."""
    src = os.path.join(temp_workspace["src"], "source.jpg")
    dst = os.path.join(temp_workspace["dst"], "dest.jpg")
    image_creator(src, content=b"content-a")

    # Simulate cross-device rename failure followed by stream-copy error
    with patch(
        "services.file_service.os.rename", side_effect=OSError("cross-device")
    ), patch("services.file_service._stream_copy", side_effect=IOError("disk full")):
        with pytest.raises(IOError):
            safe_move(src, dst)

    # Source file MUST still exist because move failed
    assert os.path.exists(src)
    assert not os.path.exists(dst)


def test_get_non_conflicting_path_no_conflict(temp_workspace, image_creator):
    """Test get_non_conflicting_path returns original path when no conflict exists."""
    src = os.path.join(temp_workspace["src"], "source.jpg")
    image_creator(src, content=b"dummy")

    dst_path, is_skip = get_non_conflicting_path(
        temp_workspace["dst"], "2026-06-01", "photo.jpg", src
    )
    assert dst_path == os.path.join(temp_workspace["dst"], "2026-06-01", "photo.jpg")
    assert is_skip is False


def test_get_non_conflicting_path_skip_identical(temp_workspace, image_creator):
    """Test get_non_conflicting_path flags is_skip when an identical file exists."""
    src = os.path.join(temp_workspace["src"], "photo.jpg")
    image_creator(src, content=b"identical-file-bytes")

    dst_file = os.path.join(temp_workspace["dst"], "2026-06-01", "photo.jpg")
    image_creator(dst_file, content=b"identical-file-bytes")

    dst_path, is_skip = get_non_conflicting_path(
        temp_workspace["dst"], "2026-06-01", "photo.jpg", src
    )
    assert dst_path == dst_file
    assert is_skip is True


def test_get_non_conflicting_path_rename_conflict(temp_workspace, image_creator):
    """Test get_non_conflicting_path renames conflicting files with different content."""
    src = os.path.join(temp_workspace["src"], "photo.jpg")
    image_creator(src, content=b"new-content")

    dst_file = os.path.join(temp_workspace["dst"], "2026-06-01", "photo.jpg")
    image_creator(dst_file, content=b"old-content")

    dst_path, is_skip = get_non_conflicting_path(
        temp_workspace["dst"], "2026-06-01", "photo.jpg", src
    )
    assert dst_path == os.path.join(temp_workspace["dst"], "2026-06-01", "photo_1.jpg")
    assert is_skip is False


def test_get_non_conflicting_path_limit_exhausted(
    temp_workspace, image_creator, monkeypatch
):
    """Test get_non_conflicting_path raises error when rename limit is reached."""
    monkeypatch.setattr(Config, "MAX_RENAME_ATTEMPTS", 2)

    src = os.path.join(temp_workspace["src"], "photo.jpg")
    image_creator(src, content=b"new-content")

    # Fill up names: base, suffix _1, suffix _2
    image_creator(
        os.path.join(temp_workspace["dst"], "2026-06-01", "photo.jpg"),
        content=b"diff-1",
    )
    image_creator(
        os.path.join(temp_workspace["dst"], "2026-06-01", "photo_1.jpg"),
        content=b"diff-2",
    )
    image_creator(
        os.path.join(temp_workspace["dst"], "2026-06-01", "photo_2.jpg"),
        content=b"diff-3",
    )

    with pytest.raises(RuntimeError):
        get_non_conflicting_path(temp_workspace["dst"], "2026-06-01", "photo.jpg", src)


def test_are_files_identical_mtime_irrelevant(temp_workspace, image_creator):
    """Test that mtime differences do not affect identity — only size+SHA-256 matter (Issue #20)."""
    src = os.path.join(temp_workspace["src"], "a.jpg")
    dst = os.path.join(temp_workspace["dst"], "b.jpg")
    image_creator(src, content=b"identical-content")
    image_creator(dst, content=b"identical-content")

    now = time.time()
    from services.file_service import are_files_identical_optimized

    # Same content, same mtime → True
    os.utime(src, (now, now))
    os.utime(dst, (now, now))
    assert are_files_identical_optimized(src, dst, optimize=True) is True

    # Same content, different mtime → still True (mtime mismatch must not cause False)
    os.utime(dst, (now - 100, now - 100))
    assert are_files_identical_optimized(src, dst, optimize=True) is True

    # Different content, different mtime → False (SHA-256 distinguishes them)
    image_creator(dst, content=b"different-content")
    os.utime(dst, (now - 100, now - 100))
    assert are_files_identical_optimized(src, dst, optimize=True) is False


def test_get_non_conflicting_path_optimized(temp_workspace, image_creator):
    """Test that files with different mtimes but identical content are still skipped."""
    src = os.path.join(temp_workspace["src"], "photo.jpg")
    image_creator(src, content=b"same-size-bytes")

    dst_file = os.path.join(temp_workspace["dst"], "2026-06-01", "photo.jpg")
    image_creator(dst_file, content=b"same-size-bytes")

    # Change destination file mtime to simulate copy from external storage
    os.utime(dst_file, (time.time() - 100, time.time() - 100))

    # With optimization: mtimes differ, but SHA-256 matches -> identical -> skip (Issue #20 fix)
    dst_path, is_skip = get_non_conflicting_path(
        temp_workspace["dst"], "2026-06-01", "photo.jpg", src, optimize=True
    )
    assert dst_path == dst_file
    assert is_skip is True

    # Without optimization: hashes are compared -> identical -> skip
    dst_path, is_skip = get_non_conflicting_path(
        temp_workspace["dst"], "2026-06-01", "photo.jpg", src, optimize=False
    )
    assert dst_path == dst_file
    assert is_skip is True
