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


def test_phash_column_and_saving():
    """Verifies that phash column exists and can store/retrieve perceptual hash."""
    db_service.register_session("session-phash", "copy")
    dummy_phash = "0123456789abcdef"
    db_service.log_file_action(
        session_id="session-phash",
        original_path="/src/p.jpg",
        organized_path="/dst/2026/p.jpg",
        file_size=500,
        sha256="hash-p",
        mtime=1.0,
        phash=dummy_phash,
    )

    with db_service.db_session() as conn:
        cursor = conn.execute(
            "SELECT phash FROM file_history WHERE session_id = 'session-phash'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["phash"] == dummy_phash


def test_log_file_action_without_phash_compatibility():
    """Verifies backward-compatibility when phash is omitted."""
    db_service.register_session("session-no-phash", "copy")
    db_service.log_file_action(
        session_id="session-no-phash",
        original_path="/src/np.jpg",
        organized_path="/dst/2026/np.jpg",
        file_size=600,
        sha256="hash-np",
        mtime=2.0,
    )

    with db_service.db_session() as conn:
        cursor = conn.execute(
            "SELECT phash FROM file_history WHERE session_id = 'session-no-phash'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["phash"] is None


def test_db_migration_from_legacy_schema(tmp_path):
    """Verifies that an older DB without phash column is migrated gracefully."""
    import sqlite3

    legacy_db = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(legacy_db))
    # Create legacy table without phash column
    conn.execute("""
        CREATE TABLE file_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            original_path TEXT NOT NULL,
            organized_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            mtime REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    # Point Config to legacy db and run initialize_db
    orig_db = Config.DB_FILE
    try:
        Config.DB_FILE = str(legacy_db)
        db_service.initialize_db()

        with db_service.db_session() as c:
            cursor = c.execute("PRAGMA table_info(file_history)")
            cols = [row["name"] for row in cursor.fetchall()]
            assert "phash" in cols
    finally:
        Config.DB_FILE = orig_db
