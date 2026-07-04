import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from config import Config
from services.file_service import get_non_conflicting_path, safe_copy, safe_move
from utils.date_utils import get_exif_date
from utils.i18n import get_txt

# Thread-safe cancellation event
cancel_event = threading.Event()


def scan_directories(src_dirs, extensions=None, date_start=None, date_end=None):
    """Scans all source directories and collects a list of file paths.

    Filters files by extension and date range if provided.
    Skips hidden files (starting with dot) and directories.
    """
    files_to_process = []
    for d in src_dirs:
        if not os.path.isdir(d):
            raise FileNotFoundError(f"Source directory does not exist: {d}")

        dir_files = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
        dir_files = [f for f in dir_files if not f.startswith(".")]
        for f in dir_files:
            filepath = os.path.join(d, f)
            ext = os.path.splitext(f)[1].lower()

            # 1. Filter by extension
            if extensions:
                if ext not in [e.lower() for e in extensions]:
                    continue
            else:
                if ext not in Config.IMAGE_EXTENSIONS:
                    continue

            # 2. Filter by date range
            if date_start or date_end:
                dt = get_exif_date(filepath)
                if not dt:
                    mtime = os.path.getmtime(filepath)
                    dt = datetime.fromtimestamp(mtime)

                file_date_str = dt.strftime("%Y-%m-%d")
                if date_start and file_date_str < date_start:
                    continue
                if date_end and file_date_str > date_end:
                    continue

            files_to_process.append((d, f))

    return files_to_process


def check_db_duplicate(src_path):
    """Checks if a file with the same size/hash is already in the database.

    Uses size-filtering to avoid calculating SHA-256 for unique files.
    """
    try:
        from services.db_service import db_session
        from services.file_service import calculate_sha256

        if not os.path.exists(src_path):
            return None

        size = os.path.getsize(src_path)

        with db_session() as conn:
            cursor = conn.execute(
                "SELECT organized_path, sha256 FROM file_history WHERE file_size = ? AND status = 'active'",
                (size,),
            )
            candidates = cursor.fetchall()

            if not candidates:
                return None

            src_hash = calculate_sha256(src_path)
            for cand in candidates:
                if cand["sha256"] == src_hash:
                    return cand["organized_path"]
    except Exception as e:
        logging.error(f"Error checking DB duplicate for {src_path}: {e}")

    return None


def parse_naming_template(template_str, dt, original_filename):
    """Parses a custom naming template and returns the relative destination path."""
    base, ext = os.path.splitext(original_filename)

    result = template_str
    result = result.replace("{YYYY}", dt.strftime("%Y"))
    result = result.replace("{MM}", dt.strftime("%m"))
    result = result.replace("{DD}", dt.strftime("%d"))
    result = result.replace("{filename}", base)
    result = result.replace("{ext}", ext)

    return result


def process_file_task(
    s_dir,
    filename,
    dst_dir,
    naming_rule,
    mode,
    dry_run,
    local_cancel_event,
    session_id=None,
    lang="ja",
):
    """Processes a single file. Used inside worker threads."""
    if local_cancel_event.is_set():
        return {
            "status": "cancelled",
            "filename": filename,
            "src_dir": os.path.basename(s_dir),
            "log_type": "error",
        }

    src_path = os.path.join(s_dir, filename)
    src_dirname = os.path.basename(s_dir)

    # 1. SQLite Database Duplicate Check (session-transcending duplicate check)
    try:
        duplicate_path = check_db_duplicate(src_path)
        if duplicate_path:
            return {
                "status": "success",
                "filename": filename,
                "src_dir": src_dirname,
                "folder": os.path.basename(os.path.dirname(duplicate_path)),
                "action": "skip",
                "copied": False,
                "message": get_txt(
                    lang,
                    "skip_db_success" if not dry_run else "dryrun_skip_db",
                    dir=src_dirname,
                    file=filename,
                    target=os.path.basename(duplicate_path),
                ),
                "log_type": "skip",
            }
    except Exception as db_err:
        logging.error(f"Error in DB duplicate check: {db_err}")

    try:
        # EXIF優先、なければ更新日時
        dt = get_exif_date(src_path)
        if not dt:
            mtime = os.path.getmtime(src_path)
            dt = datetime.fromtimestamp(mtime)

        # Apply legacy rules or custom naming templates
        if "%" in naming_rule:
            folder_name = dt.strftime(naming_rule)
            target_filename = filename
        elif naming_rule in Config.NAMING_RULES:
            date_format = Config.NAMING_RULES[naming_rule]
            folder_name = dt.strftime(date_format)
            target_filename = filename
        else:
            target_rel_path = parse_naming_template(naming_rule, dt, filename)
            if "{filename}" not in naming_rule:
                target_rel_path = os.path.join(target_rel_path, filename)
            folder_name = os.path.dirname(target_rel_path)
            target_filename = os.path.basename(target_rel_path)

        if dry_run:
            folder_path = os.path.join(dst_dir, folder_name)
            dst_path = os.path.join(folder_path, target_filename)

            action = "copy"
            target_path = dst_path

            if os.path.exists(dst_path):
                try:
                    resolved_path, is_skip = get_non_conflicting_path(
                        dst_dir, folder_name, target_filename, src_path, optimize=True
                    )
                    action = "skip" if is_skip else "rename"
                    target_path = resolved_path
                except Exception:
                    action = "error"

            if mode == "move" and action not in ("skip", "error"):
                action = "move" if action == "copy" else "rename_move"

            msg_map = {
                "copy": get_txt(
                    lang,
                    "dryrun_copy",
                    dir=src_dirname,
                    file=filename,
                    folder=folder_name,
                ),
                "move": get_txt(
                    lang,
                    "dryrun_move",
                    dir=src_dirname,
                    file=filename,
                    folder=folder_name,
                ),
                "skip": get_txt(lang, "dryrun_skip", dir=src_dirname, file=filename),
                "rename": get_txt(
                    lang,
                    "dryrun_rename_copy",
                    dir=src_dirname,
                    file=filename,
                    folder=folder_name,
                    target=os.path.basename(target_path),
                ),
                "rename_move": get_txt(
                    lang,
                    "dryrun_rename_move",
                    dir=src_dirname,
                    file=filename,
                    folder=folder_name,
                    target=os.path.basename(target_path),
                ),
                "error": get_txt(lang, "dryrun_error", dir=src_dirname, file=filename),
            }

            log_type_map = {
                "copy": "success",
                "move": "success",
                "skip": "skip",
                "rename": "rename",
                "rename_move": "rename",
                "error": "error",
            }

            return {
                "status": "success",
                "filename": filename,
                "src_dir": src_dirname,
                "folder": folder_name,
                "action": action,
                "target": os.path.basename(target_path),
                "message": msg_map.get(
                    action, f"Planned: {src_dirname}/{filename} -> {folder_name}/"
                ),
                "log_type": log_type_map.get(action, "info"),
            }

        # 実際の処理 (Copy または Move)
        dst_path, is_skip = get_non_conflicting_path(
            dst_dir, folder_name, target_filename, src_path, optimize=True
        )
        resolved_folder_path = os.path.dirname(dst_path)
        resolved_filename = os.path.basename(dst_path)

        os.makedirs(resolved_folder_path, exist_ok=True)

        copied = False
        action_done = "skip"
        log_type = "skip"

        if not is_skip:
            if mode == "move":
                safe_move(src_path, dst_path)
                copied = True
                action_done = "move"
                log_type = "success"
                message = get_txt(
                    lang,
                    "move_success",
                    dir=src_dirname,
                    file=filename,
                    folder=folder_name,
                    target=resolved_filename,
                )
            else:
                safe_copy(src_path, dst_path)
                copied = True
                action_done = "copy"
                log_type = "success"
                message = get_txt(
                    lang,
                    "copy_success",
                    dir=src_dirname,
                    file=filename,
                    folder=folder_name,
                    target=resolved_filename,
                )

            # Log action to SQLite database
            if session_id:
                try:
                    from services.db_service import log_file_action
                    from services.file_service import calculate_sha256

                    size = os.path.getsize(dst_path)
                    sha = calculate_sha256(dst_path)
                    mtime_val = os.path.getmtime(dst_path)
                    log_file_action(
                        session_id, src_path, dst_path, size, sha, mtime_val
                    )
                except Exception as db_err:
                    logging.error(f"Failed to log file action: {db_err}")
        else:
            message = get_txt(
                lang,
                "skip_success",
                dir=src_dirname,
                file=filename,
                folder=folder_name,
                target=resolved_filename,
            )

        return {
            "status": "success",
            "filename": filename,
            "src_dir": src_dirname,
            "folder": folder_name,
            "action": action_done,
            "copied": copied,
            "message": message,
            "log_type": log_type,
        }

    except Exception as e:
        return {
            "status": "error",
            "filename": filename,
            "src_dir": src_dirname,
            "message": get_txt(
                lang, "process_error", dir=src_dirname, file=filename, error=str(e)
            ),
            "log_type": "error",
        }


def arrange_photos(
    src_dirs,
    dst_dir,
    naming_rule="YYYY-MM-DD",
    mode="copy",
    dry_run=False,
    max_workers=None,
    extensions=None,
    date_start=None,
    date_end=None,
    lang="ja",
):
    """Executes the photo arrangement process and yields progress data as SSE chunks."""
    cancel_event.clear()

    # Start message logging
    start_msg = get_txt(lang, "start_dryrun" if dry_run else "start_arrange", mode=mode)
    logging.info(
        f"{start_msg} Source directories: {src_dirs}, Target: {dst_dir}, Naming: {naming_rule}"
    )

    # 1. Register session in database if actual run
    import uuid

    session_id = None
    if not dry_run:
        try:
            from services.db_service import register_session

            session_id = uuid.uuid4().hex
            register_session(session_id, mode)
        except Exception as db_err:
            logging.error(f"Failed to register session: {db_err}")

    # 2. Scan and filter files
    files_to_process = []
    for d in src_dirs:
        try:
            files_to_process.extend(
                scan_directories(
                    [d], extensions=extensions, date_start=date_start, date_end=date_end
                )
            )
        except Exception as e:
            err_msg = get_txt(lang, "scan_error", dir=d, error=str(e))
            logging.error(err_msg)
            yield f"data: {json.dumps({'status': 'error', 'message': err_msg, 'log_type': 'error'}, ensure_ascii=False)}\n\n"
            return

    total_files = len(files_to_process)
    if total_files == 0:
        msg = get_txt(lang, "no_files")
        logging.info(msg)
        yield f"data: {json.dumps({'status': 'completed', 'message': msg, 'progress': 100, 'log_type': 'info'}, ensure_ascii=False)}\n\n"
        return

    copied_count = 0
    skipped_count = 0
    error_count = 0

    if max_workers is None:
        max_workers = (
            Config.MAX_WORKERS_DRYRUN if dry_run else Config.MAX_WORKERS_ARRANGE
        )

    threads_started_msg = get_txt(
        lang, "threads_started", workers=max_workers, total=total_files
    )
    logging.info(threads_started_msg)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_file_task,
                s_dir,
                filename,
                dst_dir,
                naming_rule,
                mode,
                dry_run,
                cancel_event,
                session_id,
                lang,
            ): (s_dir, filename)
            for s_dir, filename in files_to_process
        }

        for idx, future in enumerate(as_completed(futures)):
            if cancel_event.is_set():
                cancel_msg = get_txt(lang, "user_cancelled")
                logging.warning(cancel_msg)
                yield f"data: {json.dumps({'status': 'cancelled', 'message': cancel_msg, 'log_type': 'error'}, ensure_ascii=False)}\n\n"
                for f in futures:
                    f.cancel()
                return

            try:
                res = future.result()
            except Exception as e:
                s_dir, filename = futures[future]
                res = {
                    "status": "error",
                    "filename": filename,
                    "src_dir": os.path.basename(s_dir),
                    "message": get_txt(
                        lang,
                        "unexpected_error",
                        dir=os.path.basename(s_dir),
                        file=filename,
                        error=str(e),
                    ),
                    "log_type": "error",
                }

            if res["status"] == "success":
                act = res["action"]
                if act in ("copy", "move", "rename", "rename_move"):
                    copied_count += 1
                elif act == "skip":
                    skipped_count += 1
                elif act == "error":
                    error_count += 1

                logging.info(res["message"])
            else:
                error_count += 1
                logging.error(res["message"])

            progress = int((idx + 1) / total_files * 100)

            progress_payload = {
                "status": "processing",
                "current_file": f"{res.get('src_dir')}/{res.get('filename')}",
                "copied": res.get("copied", False),
                "action": res.get("action"),
                "progress": progress,
                "message": res.get("message"),
                "log_type": res.get("log_type", "info"),
                "stats": {
                    "total": total_files,
                    "copied": copied_count,
                    "skipped": skipped_count,
                    "errors": error_count,
                },
            }
            yield f"data: {json.dumps(progress_payload, ensure_ascii=False)}\n\n"

    status_text = "シミュレーション完了" if dry_run else "処理完了"
    done_msg = get_txt(
        lang,
        "done_dryrun" if dry_run else "done_arrange",
        total=total_files,
        copied=copied_count,
        skipped=skipped_count,
        errors=error_count,
    )
    logging.info(done_msg)

    done_payload = {
        "status": "completed",
        "message": done_msg,
        "progress": 100,
        "log_type": "success",
    }
    yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
