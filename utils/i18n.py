# Translations catalog for multi-language support (i18n)

TRANSLATIONS = {
    "ja": {
        "start_dryrun": "シミュレーション（Dry Run）を開始します...",
        "start_arrange": "整理処理 ({mode}モード) を開始します...",
        "scan_error": "スキャンエラー ({dir}): {error}",
        "no_files": "処理対象ファイルがありません。",
        "threads_started": "ThreadPoolExecutorを起動しました（スレッド数: {workers}）。処理対象ファイル: {total} 件",
        "user_cancelled": "ユーザーによって処理がキャンセルされました。",
        "unexpected_error": "エラー: {dir}/{file} の処理中に予期しない例外が発生しました ({error})",
        "process_error": "エラー: {dir}/{file} の処理に失敗しました ({error})",
        "dryrun_copy": "新規コピー: {dir}/{file} -> {folder}/",
        "dryrun_move": "新規移動: {dir}/{file} -> {folder}/",
        "dryrun_skip": "スキップ（同一ファイル存在）: {dir}/{file}",
        "dryrun_skip_db": "スキップ（データベース重複）: {dir}/{file} (既に {target} として整理済みです)",
        "dryrun_rename_copy": "名前衝突回避コピー: {dir}/{file} -> {folder}/{target}",
        "dryrun_rename_move": "名前衝突回避移動: {dir}/{file} -> {folder}/{target}",
        "dryrun_error": "検証エラー: {dir}/{file}",
        "copy_success": "コピー成功: {dir}/{file} -> {folder}/{target}",
        "move_success": "移動成功: {dir}/{file} -> {folder}/{target}",
        "skip_success": "スキップ（既に存在します）: {dir}/{file} -> {folder}/{target}",
        "skip_db_success": "スキップ（データベース重複）: {dir}/{file} (既に {target} として整理済みです)",
        "done_dryrun": "シミュレーション完了: 合計 {total} 件 (完了/予定: {copied} 件, スキップ: {skipped} 件, エラー: {errors} 件)",
        "done_arrange": "処理完了: 合計 {total} 件 (完了/予定: {copied} 件, スキップ: {skipped} 件, エラー: {errors} 件)",
    },
    "en": {
        "start_dryrun": "Starting simulation (Dry Run)...",
        "start_arrange": "Starting arrangement process ({mode} mode)...",
        "scan_error": "Scan error ({dir}): {error}",
        "no_files": "No target files found to process.",
        "threads_started": "Started ThreadPoolExecutor with {workers} workers. Total files: {total}",
        "user_cancelled": "Operation cancelled by user.",
        "unexpected_error": "Error: Unexpected exception during processing {dir}/{file} ({error})",
        "process_error": "Error: Failed to process {dir}/{file} ({error})",
        "dryrun_copy": "New Copy: {dir}/{file} -> {folder}/",
        "dryrun_move": "New Move: {dir}/{file} -> {folder}/",
        "dryrun_skip": "Skip (identical file exists): {dir}/{file}",
        "dryrun_skip_db": "Skip (DB Duplicate): {dir}/{file} (already organized as {target})",
        "dryrun_rename_copy": "Rename Copy: {dir}/{file} -> {folder}/{target}",
        "dryrun_rename_move": "Rename Move: {dir}/{file} -> {folder}/{target}",
        "dryrun_error": "Validation Error: {dir}/{file}",
        "copy_success": "Copy Success: {dir}/{file} -> {folder}/{target}",
        "move_success": "Move Success: {dir}/{file} -> {folder}/{target}",
        "skip_success": "Skip (already exists): {dir}/{file} -> {folder}/{target}",
        "skip_db_success": "Skip (DB Duplicate): {dir}/{file} (already organized as {target})",
        "done_dryrun": "Simulation Completed: Total {total} (Success: {copied}, Skip: {skipped}, Error: {errors})",
        "done_arrange": "Arrangement Completed: Total {total} (Success: {copied}, Skip: {skipped}, Error: {errors})",
    },
}


def get_txt(lang, key, **kwargs):
    """Translates a key based on the selected language and formats with kwargs."""
    locale = lang if lang in TRANSLATIONS else "ja"
    template = TRANSLATIONS[locale].get(key, key)
    try:
        return template.format(**kwargs)
    except Exception:
        return template
