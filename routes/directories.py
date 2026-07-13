import logging

from flask import Blueprint, jsonify

from routes.system import _require_localhost, _verify_csrf
from utils.platform_utils import select_dir_dialog

directories_bp = Blueprint("directories", __name__)


@directories_bp.route("/api/select-dir", methods=["POST"])
def select_dir():
    """Endpoint to trigger the native folder selection dialog."""
    _require_localhost()
    _verify_csrf()
    try:
        path = select_dir_dialog()
        return jsonify({"path": path})
    except NotImplementedError:
        return jsonify({"error": "未対応のOSです。手動でパスを入力してください。"}), 400
    except Exception as e:
        logging.error(f"Error selecting directory: {e}")
        return jsonify({"error": str(e)}), 500
