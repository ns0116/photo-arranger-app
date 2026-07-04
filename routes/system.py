import logging
import os
import signal

from flask import Blueprint, jsonify, render_template

system_bp = Blueprint("system", __name__)


@system_bp.route("/")
def index():
    """Renders the main frontend application screen."""
    return render_template("index.html")


@system_bp.route("/api/shutdown", methods=["POST"])
def shutdown():
    """Gracefully terminates the Flask server process using SIGINT."""
    try:
        logging.info("Shutdown requested from client. Terminating process...")
        os.kill(os.getpid(), signal.SIGINT)
        return jsonify({"message": "サーバーをシャットダウンしています..."})
    except Exception as e:
        logging.error(f"Error executing server shutdown: {e}")
        return jsonify({"error": str(e)}), 500


def clean_parent_folders(path):
    """Recursively removes empty parent directories starting from the file path."""
    current = os.path.dirname(path)
    while current:
        try:
            if os.path.exists(current) and not os.listdir(current):
                os.rmdir(current)
                current = os.path.dirname(current)
            else:
                break
        except Exception:
            break


@system_bp.route("/api/undo", methods=["POST"])
def undo():
    """Rollbacks the file operations of the latest active session."""
    from services.db_service import (
        get_latest_session,
        get_session_history,
        mark_session_undone,
    )
    from services.file_service import safe_move

    try:
        session = get_latest_session()
        if not session:
            return jsonify({"error": "Undo可能なセッションが見つかりません。"}), 400

        if session["status"] == "undone":
            return jsonify({"error": "最新のセッションは既にUndo済みです。"}), 400

        session_id = session["session_id"]
        mode = session["mode"]
        history = get_session_history(session_id)

        undone_count = 0
        error_count = 0
        messages = []

        for item in history:
            if item["status"] != "active":
                continue

            org_path = item["organized_path"]
            orig_path = item["original_path"]

            try:
                if mode == "move":
                    if os.path.exists(org_path):
                        # Revert move: safe_move back to original location
                        safe_move(org_path, orig_path)
                        undone_count += 1
                        messages.append(
                            f"復元成功 (元に戻しました): {os.path.basename(orig_path)}"
                        )
                    else:
                        error_count += 1
                        messages.append(
                            f"復元失敗 (整理先ファイルが見つかりません): {os.path.basename(orig_path)}"
                        )
                else:  # copy mode
                    if os.path.exists(org_path):
                        os.remove(org_path)
                        undone_count += 1
                        messages.append(
                            f"削除成功 (コピー先を削除しました): {os.path.basename(org_path)}"
                        )
                    else:
                        error_count += 1
                        messages.append(
                            f"削除失敗 (コピー先ファイルが見つかりません): {os.path.basename(org_path)}"
                        )

                # Clean empty parent folders
                clean_parent_folders(org_path)

            except Exception as e:
                error_count += 1
                messages.append(f"復元失敗: {os.path.basename(orig_path)} ({str(e)})")

        # Mark the session and file records as undone in the DB
        mark_session_undone(session_id)

        return jsonify(
            {
                "message": f"Undoが完了しました。成功: {undone_count} 件, 失敗/エラー: {error_count} 件",
                "logs": messages,
                "stats": {"undone": undone_count, "errors": error_count},
            }
        )
    except Exception as e:
        logging.error(f"Error in Undo endpoint: {e}")
        return jsonify({"error": str(e)}), 500
