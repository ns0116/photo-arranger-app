from datetime import datetime

from services import db_service


def test_report_empty_history(client):
    """Test GET /api/report returns zeroed totals and an empty monthly list when no history exists."""
    response = client.get("/api/report")
    assert response.status_code == 200

    data = response.get_json()
    assert data["totals"] == {
        "total_sessions": 0,
        "total_files": 0,
        "copy_files": 0,
        "move_files": 0,
        "total_size": 0,
    }
    assert data["monthly"] == []


def test_report_mixed_copy_and_move_sessions(client):
    """Test GET /api/report aggregates counts, sizes, and copy/move split across sessions."""
    db_service.register_session("session-copy", "copy")
    db_service.log_file_action(
        session_id="session-copy",
        original_path="/src/a.jpg",
        organized_path="/dst/2026-07-01/a.jpg",
        file_size=1000,
        sha256="hash-a",
        mtime=1.0,
    )
    db_service.log_file_action(
        session_id="session-copy",
        original_path="/src/b.jpg",
        organized_path="/dst/2026-07-01/b.jpg",
        file_size=2000,
        sha256="hash-b",
        mtime=2.0,
    )

    db_service.register_session("session-move", "move")
    db_service.log_file_action(
        session_id="session-move",
        original_path="/src/c.jpg",
        organized_path="/dst/2026-07-02/c.jpg",
        file_size=500,
        sha256="hash-c",
        mtime=3.0,
    )

    response = client.get("/api/report")
    assert response.status_code == 200
    data = response.get_json()

    assert data["totals"] == {
        "total_sessions": 2,
        "total_files": 3,
        "copy_files": 2,
        "move_files": 1,
        "total_size": 3500,
    }

    # All sessions were just registered "now", so they fall in a single month bucket.
    assert len(data["monthly"]) == 1
    month_entry = data["monthly"][0]
    current_month = datetime.now().strftime("%Y-%m")
    assert month_entry["month"] == current_month
    assert month_entry["sessions"] == 2
    assert month_entry["total_files"] == 3
    assert month_entry["copy_files"] == 2
    assert month_entry["move_files"] == 1
    assert month_entry["total_size"] == 3500


def test_report_excludes_undone_files_but_counts_session(client):
    """Test that files reversed via Undo are excluded from file/size totals, while the session itself still counts."""
    db_service.register_session("session-1", "copy")
    db_service.log_file_action(
        session_id="session-1",
        original_path="/src/x.jpg",
        organized_path="/dst/2026-07-01/x.jpg",
        file_size=1234,
        sha256="hash-x",
        mtime=1.0,
    )
    db_service.mark_session_undone("session-1")

    response = client.get("/api/report")
    assert response.status_code == 200
    data = response.get_json()

    # Session still counts as an executed run, but its (reversed) files are excluded.
    assert data["totals"]["total_sessions"] == 1
    assert data["totals"]["total_files"] == 0
    assert data["totals"]["copy_files"] == 0
    assert data["totals"]["move_files"] == 0
    assert data["totals"]["total_size"] == 0

    # The month bucket still shows up (via the sessions LEFT JOIN) with zero file counts.
    assert len(data["monthly"]) == 1
    assert data["monthly"][0]["sessions"] == 1
    assert data["monthly"][0]["total_files"] == 0


def test_report_session_without_files(client):
    """Test a registered session with no logged files still appears with zeroed file stats."""
    db_service.register_session("session-empty", "copy")

    response = client.get("/api/report")
    assert response.status_code == 200
    data = response.get_json()

    assert data["totals"]["total_sessions"] == 1
    assert data["totals"]["total_files"] == 0
    assert len(data["monthly"]) == 1
    assert data["monthly"][0]["sessions"] == 1
    assert data["monthly"][0]["total_files"] == 0
