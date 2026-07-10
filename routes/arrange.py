import os

from flask import Blueprint, Response, abort, current_app, jsonify, request

from services.photo_service import arrange_photos, cancel_event

arrange_bp = Blueprint("arrange", __name__)


def _verify_csrf():
    token = request.headers.get("X-CSRF-Token", "")
    expected = current_app.config.get("CSRF_TOKEN", "")
    if not token or token != expected:
        abort(403)


@arrange_bp.route("/api/arrange", methods=["POST"])
def arrange():
    """Start the photo arrangement process and stream progress via SSE."""
    _verify_csrf()
    data = request.json or {}
    src_dirs = data.get("src_dirs")
    dst_dir = data.get("dst_dir")
    naming_rule = data.get("naming_rule", "YYYY-MM-DD")
    mode = data.get("mode", "copy")  # 'copy' or 'move'
    dry_run = data.get("dry_run", False)
    extensions = data.get("extensions")
    date_start = data.get("date_start")
    date_end = data.get("date_end")
    lang = data.get("lang", "ja")

    # Fallback to single src_dir for compatibility
    if not src_dirs and data.get("src_dir"):
        src_dirs = [data.get("src_dir")]

    if not src_dirs or not dst_dir:
        return (
            jsonify({"error": "コピー元とコピー先のディレクトリを指定してください。"}),
            400,
        )

    src_dirs = [d.strip() for d in src_dirs if d and d.strip()]
    if not src_dirs:
        return jsonify({"error": "コピー元ディレクトリを指定してください。"}), 400

    for d in src_dirs:
        if not os.path.isdir(d):
            return jsonify({"error": f"コピー元ディレクトリが存在しません: {d}"}), 400

    if not os.path.isdir(dst_dir):
        return jsonify({"error": "コピー先ディレクトリが存在しません。"}), 400

    return Response(
        arrange_photos(
            src_dirs,
            dst_dir,
            naming_rule,
            mode,
            dry_run,
            extensions=extensions,
            date_start=date_start,
            date_end=date_end,
            lang=lang,
        ),
        mimetype="text/event-stream",
    )


@arrange_bp.route("/api/cancel", methods=["POST"])
def cancel():
    """Cancel the ongoing arrangement process."""
    _verify_csrf()
    cancel_event.set()
    return jsonify({"message": "キャンセルシグナルを送信しました。"})
