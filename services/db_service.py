import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from config import Config


@contextmanager
def db_session():
    """Provides a thread-safe context manager for database sessions."""
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    conn = sqlite3.connect(Config.DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Database session error: {e}")
        raise e
    finally:
        conn.close()


def initialize_db():
    """Initializes the database schema if tables do not exist."""
    with db_session() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS file_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                original_path TEXT NOT NULL,
                organized_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                mtime REAL NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """
        )
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN dst_dir TEXT")
        except Exception:
            pass  # Column already exists
    logging.info("SQLite database initialized successfully.")


def register_session(session_id, mode, dst_dir=None):
    """Registers a new arrangement session in the database."""
    with db_session() as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, timestamp, mode, status, dst_dir) VALUES (?, ?, ?, ?, ?)",
            (session_id, datetime.now().isoformat(), mode, "active", dst_dir),
        )
    logging.info(f"Registered session {session_id} in mode={mode}.")


def log_file_action(
    session_id, original_path, organized_path, file_size, sha256, mtime
):
    """Logs a single file movement/copy operation in the file history."""
    with db_session() as conn:
        conn.execute(
            "INSERT INTO file_history (session_id, original_path, organized_path, file_size, sha256, mtime, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                original_path,
                organized_path,
                file_size,
                sha256,
                mtime,
                "active",
            ),
        )


def find_existing_hash(sha256):
    """Queries the database to check if a file with the given SHA-256 hash has already been organized."""
    with db_session() as conn:
        cursor = conn.execute(
            "SELECT organized_path FROM file_history WHERE sha256 = ? AND status = 'active' LIMIT 1",
            (sha256,),
        )
        row = cursor.fetchone()
        return row["organized_path"] if row else None


def get_session_history(session_id):
    """Retrieves the file logs for a given session ID."""
    with db_session() as conn:
        cursor = conn.execute(
            "SELECT id, original_path, organized_path, status FROM file_history WHERE session_id = ?",
            (session_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_latest_session():
    """Retrieves the most recent active session from database."""
    with db_session() as conn:
        cursor = conn.execute(
            "SELECT session_id, mode, status, dst_dir FROM sessions ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def mark_session_undone(session_id):
    """Marks a session and its associated file logs as undone/reversed in the database."""
    with db_session() as conn:
        conn.execute(
            "UPDATE sessions SET status = 'undone' WHERE session_id = ?", (session_id,)
        )
        conn.execute(
            "UPDATE file_history SET status = 'reversed' WHERE session_id = ?",
            (session_id,),
        )
    logging.info(f"Session {session_id} has been marked as undone in DB.")
