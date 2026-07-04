import os

import pytest

from app import create_app
from config import Config
from services import db_service


@pytest.fixture
def app_client(tmp_path):
    """Initializes a Flask app test client with mock db and folder configs."""
    test_db = tmp_path / "test_history.db"
    orig_db = Config.DB_FILE
    orig_dir = Config.LOG_DIR

    Config.DB_FILE = str(test_db)
    Config.LOG_DIR = str(tmp_path)

    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client

    Config.DB_FILE = orig_db
    Config.LOG_DIR = orig_dir


def test_undo_copy_mode(app_client, tmp_path):
    """Tests that rolling back a copy operation deletes target files and empty directories."""
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    # Create source file
    test_file = src_dir / "photo.jpg"
    test_file.write_bytes(b"image data")

    # Perform actual copy arrange
    response = app_client.post(
        "/api/arrange",
        json={
            "src_dirs": [str(src_dir)],
            "dst_dir": str(dst_dir),
            "naming_rule": "YYYY-MM-DD",
            "mode": "copy",
            "dry_run": False,
        },
    )
    assert response.status_code == 200

    # Verify file copied to target folder (date named folder)
    today_str = db_service.datetime.now().strftime("%Y-%m-%d")
    copied_file = dst_dir / today_str / "photo.jpg"
    assert copied_file.exists()

    # Trigger Undo
    undo_resp = app_client.post("/api/undo")
    assert undo_resp.status_code == 200
    undo_data = undo_resp.get_json()
    assert "Undoが完了しました" in undo_data["message"]

    # Verify file is deleted
    assert not copied_file.exists()
    # Verify target date folder is cleaned up
    assert not (dst_dir / today_str).exists()
    # Verify source file is untouched
    assert test_file.exists()


def test_undo_move_mode(app_client, tmp_path):
    """Tests that rolling back a move operation safely restores files to original paths."""
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    test_file = src_dir / "photo.jpg"
    test_file.write_bytes(b"image data")

    # Perform move arrange
    response = app_client.post(
        "/api/arrange",
        json={
            "src_dirs": [str(src_dir)],
            "dst_dir": str(dst_dir),
            "naming_rule": "YYYY-MM-DD",
            "mode": "move",
            "dry_run": False,
        },
    )
    assert response.status_code == 200

    today_str = db_service.datetime.now().strftime("%Y-%m-%d")
    moved_file = dst_dir / today_str / "photo.jpg"
    assert moved_file.exists()
    assert not test_file.exists()  # Source deleted

    # Trigger Undo
    undo_resp = app_client.post("/api/undo")
    assert undo_resp.status_code == 200

    # Verify moved file returned to source
    assert test_file.exists()
    assert not moved_file.exists()
    assert not (dst_dir / today_str).exists()  # Date folder cleaned
