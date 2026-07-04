import hashlib
import os
import time
from unittest.mock import patch

import pytest

from config import Config
from services.file_service import (
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
    """Test safe_copy successfully copies file and verifies hash."""
    src = os.path.join(temp_workspace["src"], "source.jpg")
    dst = os.path.join(temp_workspace["dst"], "dest.jpg")
    content = b"ImageBytesContent"
    image_creator(src, content=content)

    assert safe_copy(src, dst) is True
    assert os.path.exists(dst)
    with open(dst, "rb") as f:
        assert f.read() == content


def test_safe_copy_hash_mismatch(temp_workspace, image_creator):
    """Test safe_copy raises IOError and cleans up target on hash mismatch."""
    src = os.path.join(temp_workspace["src"], "source.jpg")
    dst = os.path.join(temp_workspace["dst"], "dest.jpg")
    image_creator(src, content=b"content-a")

    with patch("services.file_service.calculate_sha256") as mock_hash:
        # Mock returns different hashes for source and destination to simulate corruption
        mock_hash.side_effect = ["hash-src", "hash-dst-corrupted"]
        with pytest.raises(IOError):
            safe_copy(src, dst)

    # Destination file should be cleaned up (deleted)
    assert not os.path.exists(dst)


def test_safe_move_success(temp_workspace, image_creator):
    """Test safe_move successfully copies file and deletes original source."""
    src = os.path.join(temp_workspace["src"], "source.jpg")
    dst = os.path.join(temp_workspace["dst"], "dest.jpg")
    content = b"ImageBytesContent"
    image_creator(src, content=content)

    assert safe_move(src, dst) is True
    assert os.path.exists(dst)
    assert not os.path.exists(src)


def test_safe_move_failure(temp_workspace, image_creator):
    """Test safe_move retains source file if copy/hash check fails."""
    src = os.path.join(temp_workspace["src"], "source.jpg")
    dst = os.path.join(temp_workspace["dst"], "dest.jpg")
    image_creator(src, content=b"content-a")

    with patch("services.file_service.calculate_sha256") as mock_hash:
        mock_hash.side_effect = ["hash-src", "hash-dst-corrupted"]
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


def test_get_non_conflicting_path_optimized(temp_workspace, image_creator):
    """Test two-stage verification (optimization) based on mtimes."""
    src = os.path.join(temp_workspace["src"], "photo.jpg")
    image_creator(src, content=b"same-size-bytes")

    dst_file = os.path.join(temp_workspace["dst"], "2026-06-01", "photo.jpg")
    image_creator(dst_file, content=b"same-size-bytes")

    # Change destination file mtime to simulate different metadata/times
    os.utime(dst_file, (time.time() - 100, time.time() - 100))

    # With optimization: mtimes differ -> immediately treated as different -> rename
    dst_path, is_skip = get_non_conflicting_path(
        temp_workspace["dst"], "2026-06-01", "photo.jpg", src, optimize=True
    )
    assert dst_path == os.path.join(temp_workspace["dst"], "2026-06-01", "photo_1.jpg")
    assert is_skip is False

    # Without optimization: hashes are compared -> identical -> skip
    dst_path, is_skip = get_non_conflicting_path(
        temp_workspace["dst"], "2026-06-01", "photo.jpg", src, optimize=False
    )
    assert dst_path == dst_file
    assert is_skip is True
