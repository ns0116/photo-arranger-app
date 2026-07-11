import hashlib
import logging
import os
import shutil

from config import Config


def validate_path_in_dst(dst_dir: str, candidate_path: str) -> None:
    """Raise ValueError if candidate_path is outside dst_dir (path traversal guard)."""
    dst_real = os.path.realpath(dst_dir)
    candidate_real = os.path.realpath(candidate_path)
    if candidate_real != dst_real and not candidate_real.startswith(dst_real + os.sep):
        raise ValueError(
            f"パストラバーサルが検出されました: '{candidate_real}' は '{dst_real}' の外にあります"
        )


def calculate_sha256(filepath):
    """Calculates the SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def are_files_identical_optimized(src_path, dst_path, optimize=True):
    """Checks if two files are identical using size, mtime, and SHA-256.

    If optimize is True, performs a 2-stage verification:
    - Stage 1: Fast-check size. If sizes differ, they are different (return False).
    - Stage 2: Check if mtimes also match. If optimization is enabled and mtimes differ,
      assumes they are different (to avoid expensive hashing).
      If they match in size and mtime (or optimization is disabled), computes
      and compares SHA-256 hashes to guarantee identity.
    """
    if not os.path.exists(dst_path):
        return False

    try:
        src_size = os.path.getsize(src_path)
        dst_size = os.path.getsize(dst_path)
        if src_size != dst_size:
            return False

        if optimize:
            src_mtime = os.path.getmtime(src_path)
            dst_mtime = os.path.getmtime(dst_path)
            # 1-second tolerance for floating-point differences
            if abs(src_mtime - dst_mtime) > 1.0:
                return False

        # Compare SHA-256 hashes
        return calculate_sha256(src_path) == calculate_sha256(dst_path)
    except Exception as e:
        logging.error(f"Error comparing files {src_path} and {dst_path}: {e}")
        return False


def get_non_conflicting_path(
    dst_dir, folder_name, filename, src_filepath, optimize=True
):
    """Finds a non-conflicting path for the file in the target folder.

    If an identical file (same content) already exists under the target directory,
    returns the existing file path with is_skip = True.
    If the name conflicts but the contents differ, generates a renamed path
    by appending '_1', '_2', etc. to the filename, up to MAX_RENAME_ATTEMPTS.
    """
    folder_path = os.path.join(dst_dir, folder_name)
    validate_path_in_dst(dst_dir, folder_path)
    dst_filepath = os.path.join(folder_path, filename)

    # If no file exists at destination, it's a new copy/move
    if not os.path.exists(dst_filepath):
        return dst_filepath, False

    # Check if existing file is identical to source
    if are_files_identical_optimized(src_filepath, dst_filepath, optimize=optimize):
        return dst_filepath, True

    # Resolve filename conflict by renaming
    base, ext = os.path.splitext(filename)
    counter = 1
    max_attempts = Config.MAX_RENAME_ATTEMPTS

    while counter <= max_attempts:
        new_filename = f"{base}_{counter}{ext}"
        new_dst_filepath = os.path.join(folder_path, new_filename)

        if not os.path.exists(new_dst_filepath):
            return new_dst_filepath, False

        if are_files_identical_optimized(
            src_filepath, new_dst_filepath, optimize=optimize
        ):
            return new_dst_filepath, True

        counter += 1

    raise RuntimeError(
        f"Rename attempts limit ({max_attempts}) reached for {filename}. "
        f"Too many conflicting files in folder '{folder_name}'."
    )


def _stream_copy(src_path, dst_tmp_path):
    """Copies src to dst_tmp in 64 KiB chunks, computing the src SHA-256 in one pass."""
    hasher = hashlib.sha256()
    with open(src_path, "rb") as f_in, open(dst_tmp_path, "wb") as f_out:
        for chunk in iter(lambda: f_in.read(65536), b""):
            hasher.update(chunk)
            f_out.write(chunk)
    shutil.copystat(src_path, dst_tmp_path)
    return hasher.hexdigest()


def safe_copy(src_path, dst_path):
    """安全なコピー: コピー先に一時ファイルを作成し、ハッシュ検証後にリネーム。失敗時はクリーンアップ"""
    dst_dir = os.path.dirname(dst_path)
    if dst_dir:
        os.makedirs(dst_dir, exist_ok=True)

    dst_tmp_path = dst_path + ".tmp"
    try:
        src_hash = _stream_copy(src_path, dst_tmp_path)
        tmp_hash = calculate_sha256(dst_tmp_path)

        if src_hash != tmp_hash:
            raise IOError(f"ハッシュ値が一致しません (src={src_hash}, dst={tmp_hash})")

        if os.path.exists(dst_path):
            os.remove(dst_path)
        os.rename(dst_tmp_path, dst_path)
        return True

    except Exception as e:
        logging.error(f"safe_copy rollback triggered: {str(e)}")
        for path in (dst_tmp_path, dst_path):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        raise IOError(f"コピー失敗によるロールバック実行: {str(e)}")


def safe_move(src_path, dst_path):
    """安全な移動: コピー先に一時ファイルを作成し、ハッシュ検証後にリネーム、元ファイルを削除。失敗時はクリーンアップ"""
    dst_dir = os.path.dirname(dst_path)
    if dst_dir:
        os.makedirs(dst_dir, exist_ok=True)

    dst_tmp_path = dst_path + ".tmp"
    try:
        src_hash = _stream_copy(src_path, dst_tmp_path)
        tmp_hash = calculate_sha256(dst_tmp_path)

        if src_hash != tmp_hash:
            raise IOError(f"ハッシュ値が一致しません (src={src_hash}, dst={tmp_hash})")

        if os.path.exists(dst_path):
            os.remove(dst_path)
        os.rename(dst_tmp_path, dst_path)

        os.remove(src_path)
        return True

    except Exception as e:
        logging.error(f"safe_move rollback triggered: {str(e)}")
        for path in (dst_tmp_path, dst_path):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        raise IOError(f"移動失敗によるロールバック実行: {str(e)}")
