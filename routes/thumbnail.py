import io
import logging
import os

from flask import Blueprint, Response, jsonify, request
from PIL import Image, ImageOps, UnidentifiedImageError

from config import Config
from routes.system import _require_localhost, _verify_csrf
from services.file_service import validate_path_in_dst

thumbnail_bp = Blueprint("thumbnail", __name__)

THUMBNAIL_SIZE = (150, 150)


def _is_within_allowed_dirs(path: str, allowed_dirs: list) -> bool:
    """Returns True if path resolves inside at least one of allowed_dirs.

    Reuses the same realpath-based traversal guard as the arrange flow
    (services.file_service.validate_path_in_dst) so a single source of
    truth defines what "inside a directory" means across the app.
    """
    for allowed_dir in allowed_dirs:
        try:
            validate_path_in_dst(allowed_dir, path)
            return True
        except ValueError:
            continue
    return False


@thumbnail_bp.route("/api/thumbnail", methods=["GET"])
def thumbnail():
    """Generates a small JPEG thumbnail for an image located inside an allowed source directory.

    Since this endpoint reads arbitrary files from the local filesystem based on a
    client-supplied path, it is restricted to localhost requests (matching
    /api/select-dir, /api/shutdown, /api/undo) and requires the same CSRF token as
    other endpoints. The frontend cannot attach custom headers to a plain <img src>
    request, so the client fetches the image via JS (with the CSRF header) and
    assigns the resulting blob URL to the <img> element instead.

    The caller must also pass one or more `src_dir` query parameters identifying the
    currently configured source directories (the same list sent to /api/arrange).
    The requested `path` is only served if it resolves inside one of them, preventing
    arbitrary file reads / path traversal.
    """
    _require_localhost()
    _verify_csrf()

    path = request.args.get("path", "")
    src_dirs = [d for d in request.args.getlist("src_dir") if d]

    if not path or not src_dirs:
        return jsonify({"error": "pathとsrc_dirの指定が必要です。"}), 400

    ext = os.path.splitext(path)[1].lower()
    if ext not in Config.IMAGE_EXTENSIONS:
        return jsonify({"error": "サポートされていないファイル形式です。"}), 400

    if not _is_within_allowed_dirs(path, src_dirs):
        return jsonify({"error": "許可されていないパスです。"}), 403

    if not os.path.isfile(path):
        return jsonify({"error": "ファイルが見つかりません。"}), 404

    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.thumbnail(THUMBNAIL_SIZE)

            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=85)
            buf.seek(0)

        return Response(
            buf.getvalue(),
            mimetype="image/jpeg",
            headers={"Cache-Control": "private, max-age=3600"},
        )
    except UnidentifiedImageError:
        return (
            jsonify(
                {"error": "画像を読み込めませんでした（非対応の形式または破損）。"}
            ),
            422,
        )
    except Exception as e:
        logging.error(f"Thumbnail generation failed for {path}: {e}")
        return jsonify({"error": "サムネイル生成に失敗しました。"}), 500
