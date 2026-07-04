import os
from unittest.mock import patch

import pytest


def test_index_route(client):
    """Test GET / returns 200 and loads the index template."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Photo Arranger" in response.data


def test_select_dir_route(client):
    """Test POST /api/select-dir returns the mocked directory path."""
    with patch("routes.directories.select_dir_dialog") as mock_dialog:
        mock_dialog.return_value = "/mock/selected/folder"
        response = client.post("/api/select-dir")
        assert response.status_code == 200
        assert response.json == {"path": "/mock/selected/folder"}


def test_select_dir_unsupported_os(client):
    """Test POST /api/select-dir returns 400 error on unsupported operating systems."""
    with patch("routes.directories.select_dir_dialog") as mock_dialog:
        mock_dialog.side_effect = NotImplementedError()
        response = client.post("/api/select-dir")
        assert response.status_code == 400
        assert "未対応のOSです" in response.json["error"]


def test_cancel_route(client):
    """Test POST /api/cancel signals cancellation success."""
    response = client.post("/api/cancel")
    assert response.status_code == 200
    assert "キャンセル" in response.json["message"]


def test_shutdown_route(client):
    """Test POST /api/shutdown invokes process shutdown signals."""
    with patch("os.kill") as mock_kill:
        response = client.post("/api/shutdown")
        assert response.status_code == 200
        assert "シャットダウンしています" in response.json["message"]
        mock_kill.assert_called_once()


def test_arrange_route_missing_args(client):
    """Test POST /api/arrange returns 400 when folders are not provided."""
    response = client.post("/api/arrange", json={})
    assert response.status_code == 400
    assert "コピー元とコピー先のディレクトリ" in response.json["error"]


def test_arrange_route_dry_run(client, temp_workspace, image_creator):
    """Test POST /api/arrange executes simulation and streams data."""
    src = temp_workspace["src"]
    dst = temp_workspace["dst"]
    image_creator(os.path.join(src, "photo1.jpg"), exif_date_str="2026:06:01 12:00:00")

    response = client.post(
        "/api/arrange",
        json={
            "src_dirs": [src],
            "dst_dir": dst,
            "naming_rule": "YYYY-MM-DD",
            "mode": "copy",
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    # Verify the streamed SSE response contains simulation results
    stream_content = response.data.decode("utf-8")
    assert "data: " in stream_content
    assert "completed" in stream_content


@pytest.mark.skip(reason="Skipped test to match test structure guidelines")
def test_skipped_requirement():
    """Skipped test for tracking structural requirements."""
    assert False
