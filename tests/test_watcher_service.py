import os
import time

from services.watcher_service import FolderWatcher


def test_watcher_initial_state():
    watcher = FolderWatcher()
    status = watcher.get_status()
    assert status["running"] is False
    assert status["status"] == "stopped"
    assert status["last_run"] is None


def test_watcher_start_validation_missing_dirs(temp_workspace):
    watcher = FolderWatcher()
    # No dirs
    success, msg = watcher.start({})
    assert success is False
    assert "required" in msg

    # Non-existent src dir
    success, msg = watcher.start(
        {"src_dirs": ["/non/existent/dir"], "dst_dir": temp_workspace["dst"]}
    )
    assert success is False
    assert "does not exist" in msg


def test_watcher_start_and_stop(temp_workspace):
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    watcher = FolderWatcher()

    success, msg = watcher.start({"src_dirs": [src], "dst_dir": dst, "interval": 10})
    assert success is True
    assert watcher.get_status()["running"] is True
    assert watcher.get_status()["status"] == "idle"

    # Second start while running should fail
    success2, _ = watcher.start({"src_dirs": [src], "dst_dir": dst})
    assert success2 is False

    # Stop watcher
    stop_success, _ = watcher.stop()
    assert stop_success is True
    assert watcher.get_status()["running"] is False
    assert watcher.get_status()["status"] == "stopped"


def test_watcher_check_and_arrange_copies_files(temp_workspace, image_creator):
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]

    # Create dummy images
    p1 = os.path.join(src, "watch_img1.jpg")
    image_creator(p1, exif_date_str="2026:06:01 12:00:00")

    watcher = FolderWatcher()
    success, _ = watcher.start(
        {
            "src_dirs": [src],
            "dst_dir": dst,
            "interval": 3600,  # long interval; we trigger check manually
            "mode": "copy",
            "naming_rule": "YYYY-MM-DD",
        }
    )
    assert success is True

    try:
        # First check establishes baseline snapshot (size & mtime)
        watcher._check_and_arrange()
        # Second check detects stable file and arranges it
        watcher._check_and_arrange()

        status = watcher.get_status()
        assert status["last_run"] is not None
        assert status["last_count"] >= 1
        assert os.path.exists(os.path.join(dst, "2026-06-01", "watch_img1.jpg"))

    finally:
        watcher.stop()


def test_watcher_auto_arrange_and_undo(
    client, csrf_headers, temp_workspace, image_creator
):
    """Test files arranged automatically by watcher can be undone via /api/undo."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]

    p = os.path.join(src, "move_me.jpg")
    image_creator(p, exif_date_str="2026:06:01 12:00:00")

    watcher = FolderWatcher()
    success, _ = watcher.start(
        {
            "src_dirs": [src],
            "dst_dir": dst,
            "interval": 3600,
            "mode": "move",
            "naming_rule": "YYYY-MM-DD",
        }
    )
    assert success is True

    try:
        watcher._check_and_arrange()
        watcher._check_and_arrange()

        dest_file = os.path.join(dst, "2026-06-01", "move_me.jpg")
        assert os.path.exists(dest_file)
        assert not os.path.exists(p)

        # Call undo endpoint
        undo_resp = client.post("/api/undo", headers=csrf_headers)
        assert undo_resp.status_code == 200
        assert "Undo" in undo_resp.json["message"]

        # File should be back in src and removed from dst
        assert os.path.exists(p)
        assert not os.path.exists(dest_file)

    finally:
        watcher.stop()


def test_watcher_routes(client, csrf_headers, temp_workspace):
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]

    # 1. Get status
    resp = client.get("/api/watcher/status")
    assert resp.status_code == 200
    assert "running" in resp.json

    # 2. Start watcher via API
    resp_start = client.post(
        "/api/watcher/start",
        json={"src_dirs": [src], "dst_dir": dst, "interval": 10},
        headers=csrf_headers,
    )
    assert resp_start.status_code == 200
    assert resp_start.json["status"]["running"] is True

    # 3. Stop watcher via API
    resp_stop = client.post(
        "/api/watcher/stop",
        json={},
        headers=csrf_headers,
    )
    assert resp_stop.status_code == 200
    assert resp_stop.json["status"]["running"] is False
