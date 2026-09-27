import logging

from flask import Blueprint, abort, current_app, jsonify, request

from services.watcher_service import folder_watcher

watcher_bp = Blueprint("watcher", __name__)


def _verify_csrf():
    token = request.headers.get("X-CSRF-Token", "")
    expected = current_app.config.get("CSRF_TOKEN", "")
    if not token or token != expected:
        abort(403)


@watcher_bp.route("/api/watcher/status", methods=["GET"])
def watcher_status():
    """Returns the current status of the folder watcher."""
    return jsonify(folder_watcher.get_status())


@watcher_bp.route("/api/watcher/start", methods=["POST"])
def watcher_start():
    """Starts the folder watcher daemon with the provided configuration."""
    _verify_csrf()
    data = request.json or {}

    src_dirs = data.get("src_dirs")
    if not src_dirs and data.get("src_dir"):
        src_dirs = [data.get("src_dir")]

    config = {
        "src_dirs": src_dirs or [],
        "dst_dir": data.get("dst_dir"),
        "interval": data.get("interval", 30),
        "mode": data.get("mode", "copy"),
        "naming_rule": data.get("naming_rule", "YYYY-MM-DD"),
        "rules": data.get("rules", []),
        "extensions": data.get("extensions"),
        "recursive": bool(data.get("recursive", False)),
    }

    success, message = folder_watcher.start(config)
    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message, "status": folder_watcher.get_status()})


@watcher_bp.route("/api/watcher/stop", methods=["POST"])
def watcher_stop():
    """Stops the folder watcher daemon."""
    _verify_csrf()
    success, message = folder_watcher.stop()
    return jsonify({"message": message, "status": folder_watcher.get_status()})
