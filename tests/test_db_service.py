import os

import pytest

from config import Config
from services import db_service


@pytest.fixture(autouse=True)
def mock_db_file(tmp_path):
    """Sets a temporary database file for the config class during testing."""
    test_db = tmp_path / "test_history.db"
    orig_db = Config.DB_FILE
    orig_dir = Config.LOG_DIR

    Config.DB_FILE = str(test_db)
    Config.LOG_DIR = str(tmp_path)

    db_service.initialize_db()

    yield

    Config.DB_FILE = orig_db
    Config.LOG_DIR = orig_dir


def test_db_initialization():
    """Verifies that database connection and tables are successfully set up."""
    assert os.path.exists(Config.DB_FILE)
    with db_service.db_session() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cursor.fetchall()]
        assert "sessions" in tables
        assert "file_history" in tables


def test_register_and_get_latest_session():
    """Tests session registration and retrieving the latest session."""
    db_service.register_session("session-123", "copy")
    latest = db_service.get_latest_session()
    assert latest is not None
    assert latest["session_id"] == "session-123"
    assert latest["mode"] == "copy"
    assert latest["status"] == "active"


def test_log_file_action_and_history():
    """Tests logging file operations and fetching session histories."""
    db_service.register_session("session-1", "move")
    db_service.log_file_action(
        session_id="session-1",
        original_path="/src/photo.jpg",
        organized_path="/dst/2026-06-01/photo.jpg",
        file_size=1024,
        sha256="dummyhash123",
        mtime=123456789.0,
    )

    history = db_service.get_session_history("session-1")
    assert len(history) == 1
    assert history[0]["original_path"] == "/src/photo.jpg"
    assert history[0]["organized_path"] == "/dst/2026-06-01/photo.jpg"
    assert history[0]["status"] == "active"


def test_find_existing_hash():
    """Tests lookup of existing hashes to detect duplicates across sessions."""
    db_service.register_session("session-2", "copy")
    db_service.log_file_action(
        session_id="session-2",
        original_path="/src/original.jpg",
        organized_path="/dst/2026/06/duplicate.jpg",
        file_size=2048,
        sha256="uniquehash999",
        mtime=987654321.0,
    )

    found_path = db_service.find_existing_hash("uniquehash999")
    assert found_path == "/dst/2026/06/duplicate.jpg"

    not_found = db_service.find_existing_hash("nonexistent")
    assert not_found is None


def test_mark_session_undone():
    """Tests marking a session and its file histories as undone/reversed."""
    db_service.register_session("session-3", "copy")
    db_service.log_file_action(
        session_id="session-3",
        original_path="/src/a.jpg",
        organized_path="/dst/2026-06-01/a.jpg",
        file_size=100,
        sha256="hash-a",
        mtime=1.0,
    )

    db_service.mark_session_undone("session-3")

    # Verify session is updated
    latest = db_service.get_latest_session()
    assert latest["status"] == "undone"

    # Verify file history status updated to reversed
    history = db_service.get_session_history("session-3")
    assert len(history) == 1
    assert history[0]["status"] == "reversed"
