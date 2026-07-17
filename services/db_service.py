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
        conn.execute("PRAGMA journal_mode=WAL")
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


def get_report_stats():
    """Aggregates arrange activity for the report/statistics screen.

    Buckets sessions by the month they were executed (session.timestamp) and
    joins each session's file_history rows to compute per-month totals.

    Notes on scope:
    - File/size counts only include file_history rows with status='active',
      so files that were later reverted via Undo are excluded from the
      "organized files" totals (they no longer represent organized state).
    - Session counts include every registered session (even ones later
      undone), since a session still represents an arrangement run that
      took place.
    - A LEFT JOIN is used so months with sessions that produced zero active
      file records (e.g. an errored or fully-undone run) still appear.
    """
    with db_session() as conn:
        cursor = conn.execute(
            """
            SELECT
                strftime('%Y-%m', s.timestamp) AS month,
                COUNT(DISTINCT s.session_id) AS sessions,
                COALESCE(SUM(CASE WHEN fh.status = 'active' THEN 1 ELSE 0 END), 0) AS total_files,
                COALESCE(SUM(CASE WHEN fh.status = 'active' AND s.mode = 'copy' THEN 1 ELSE 0 END), 0) AS copy_files,
                COALESCE(SUM(CASE WHEN fh.status = 'active' AND s.mode = 'move' THEN 1 ELSE 0 END), 0) AS move_files,
                COALESCE(SUM(CASE WHEN fh.status = 'active' THEN fh.file_size ELSE 0 END), 0) AS total_size
            FROM sessions s
            LEFT JOIN file_history fh ON fh.session_id = s.session_id
            GROUP BY month
            ORDER BY month
            """
        )
        monthly = [dict(row) for row in cursor.fetchall()]

        totals = {
            "total_sessions": sum(m["sessions"] for m in monthly),
            "total_files": sum(m["total_files"] for m in monthly),
            "copy_files": sum(m["copy_files"] for m in monthly),
            "move_files": sum(m["move_files"] for m in monthly),
            "total_size": sum(m["total_size"] for m in monthly),
        }

        return {"totals": totals, "monthly": monthly}


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
