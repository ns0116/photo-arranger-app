import os
import shutil
import json
import subprocess
import signal
import sys
import platform
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, Response, jsonify
from PIL import Image
from PIL.ExifTags import TAGS

# PyInstallerのパッケージング時の一時参照先を設定
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

# グローバルなキャンセル要求フラグ
is_cancelled = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/select-dir', methods=['POST'])
def select_dir():
    try:
        system = platform.system()
        if system == 'Darwin':
            # macOSネイティブのフォルダ選択ダイアログをAppleScript経由で開く
            script = 'POSIX path of (choose folder with prompt "フォルダを選択してください")'
            process = subprocess.Popen(
                ['osascript', '-e', script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                return jsonify({'path': stdout.strip()})
            return jsonify({'path': ''})
            
        elif system == 'Windows':
            # Windowsネイティブのフォルダ選択ダイアログをPowerShell経由で開く
            script = (
                "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$f.Description = 'フォルダを選択してください'; "
                "if($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $f.SelectedPath }"
            )
            process = subprocess.Popen(
                ['powershell', '-Command', script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                return jsonify({'path': stdout.strip()})
            return jsonify({'path': ''})
            
        else:
            return jsonify({'error': '未対応のOSです。手動でパスを入力してください。'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cancel', methods=['POST'])
def cancel():
    global is_cancelled
    is_cancelled = True
    return jsonify({'message': 'キャンセルシグナルを送信しました。'})

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    try:
        # プロセスに SIGINT を送って Flask を安全に停止する
        os.kill(os.getpid(), signal.SIGINT)
        return jsonify({'message': 'サーバーをシャットダウンしています...'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_exif_date(filepath):
    """画像ファイルからEXIF撮影日時を取得する"""
    try:
        with Image.open(filepath) as img:
            exif_data = img._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag, tag)
                    if tag_name in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime'):
                        if isinstance(value, str) and len(value) >= 10:
                            # "YYYY:MM:DD HH:MM:SS" -> "YYYY-MM-DD"
                            date_str = value[:10].replace(':', '-')
                            parts = date_str.split('-')
                            if len(parts) == 3 and all(p.isdigit() for p in parts):
                                return datetime.strptime(date_str, '%Y-%m-%d')
    except Exception:
        pass
    return None

def get_non_conflicting_path(dst_dir, folder_name, filename, src_filepath):
    """衝突しないコピー先パスを返す。同一内容（サイズ一致）なら skip フラグを立てる"""
    folder_path = os.path.join(dst_dir, folder_name)
    dst_filepath = os.path.join(folder_path, filename)
    
    if not os.path.exists(dst_filepath):
        return dst_filepath, False
        
    try:
        src_size = os.path.getsize(src_filepath)
        dst_size = os.path.getsize(dst_filepath)
        if src_size == dst_size:
            return dst_filepath, True  # サイズ一致のためスキップ
    except Exception:
        pass
        
    # ファイル名が衝突（サイズ不一致）したためリネーム
    base, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_filename = f"{base}_{counter}{ext}"
        new_dst_filepath = os.path.join(folder_path, new_filename)
        if not os.path.exists(new_dst_filepath):
            return new_dst_filepath, False
            
        try:
            if os.path.getsize(src_filepath) == os.path.getsize(new_dst_filepath):
                return new_dst_filepath, True
        except Exception:
            pass
        counter += 1

def process_file_task(s_dir, filename, dst_dir, date_format, mode, dry_run):
    """1つのファイルを処理するスレッド用タスク"""
    global is_cancelled
    if is_cancelled:
        return {'status': 'cancelled', 'filename': filename, 'src_dir': os.path.basename(s_dir)}
        
    src_path = os.path.join(s_dir, filename)
    src_dirname = os.path.basename(s_dir)
    
    try:
        # EXIF優先、なければ更新日時
        dt = get_exif_date(src_path)
        if not dt:
            mtime = os.path.getmtime(src_path)
            dt = datetime.fromtimestamp(mtime)
            
        folder_name = dt.strftime(date_format)
        
        if dry_run:
            folder_path = os.path.join(dst_dir, folder_name)
            dst_path = os.path.join(folder_path, filename)
            
            action = 'copy'
            target_path = dst_path
            
            if os.path.exists(dst_path):
                try:
                    src_size = os.path.getsize(src_path)
                    dst_size = os.path.getsize(dst_path)
                    if src_size == dst_size:
                        action = 'skip'
                    else:
                        resolved_path, is_skip = get_non_conflicting_path(dst_dir, folder_name, filename, src_path)
                        action = 'skip' if is_skip else 'rename'
                        target_path = resolved_path
                except Exception:
                    action = 'error'
            
            if mode == 'move' and action not in ('skip', 'error'):
                action = 'move' if action == 'copy' else 'rename_move'
                
            msg_map = {
                'copy': f"新規コピー: {src_dirname}/{filename} -> {folder_name}/",
                'move': f"新規移動: {src_dirname}/{filename} -> {folder_name}/",
                'skip': f"スキップ（同一ファイル存在）: {src_dirname}/{filename}",
                'rename': f"名前衝突回避コピー: {src_dirname}/{filename} -> {folder_name}/{os.path.basename(target_path)}",
                'rename_move': f"名前衝突回避移動: {src_dirname}/{filename} -> {folder_name}/{os.path.basename(target_path)}",
                'error': f"検証エラー: {src_dirname}/{filename}"
            }
            
            return {
                'status': 'success',
                'filename': filename,
                'src_dir': src_dirname,
                'folder': folder_name,
                'action': action,
                'target': os.path.basename(target_path),
                'message': msg_map.get(action, f"予定: {src_dirname}/{filename} -> {folder_name}/")
            }
            
        # 実際の処理 (Copy または Move)
        dst_path, is_skip = get_non_conflicting_path(dst_dir, folder_name, filename, src_path)
        resolved_folder_path = os.path.dirname(dst_path)
        resolved_filename = os.path.basename(dst_path)
        
        os.makedirs(resolved_folder_path, exist_ok=True)
        
        copied = False
        action_done = 'skip'
        
        if not is_skip:
            if mode == 'move':
                # 安全な移動 (コピー後にファイルサイズを検証して削除)
                shutil.copy2(src_path, dst_path)
                if os.path.exists(dst_path) and os.path.getsize(src_path) == os.path.getsize(dst_path):
                    os.remove(src_path)
                    copied = True
                    action_done = 'move'
                    message = f"移動成功: {src_dirname}/{filename} -> {folder_name}/{resolved_filename}"
                else:
                    raise IOError("移動先ファイルのサイズ不一致。元ファイルを保護するため削除を中止しました。")
            else:
                shutil.copy2(src_path, dst_path)
                copied = True
                action_done = 'copy'
                message = f"コピー成功: {src_dirname}/{filename} -> {folder_name}/{resolved_filename}"
        else:
            message = f"スキップ（既に存在します）: {src_dirname}/{filename} -> {folder_name}/{resolved_filename}"
            
        return {
            'status': 'success',
            'filename': filename,
            'src_dir': src_dirname,
            'folder': folder_name,
            'action': action_done,
            'copied': copied,
            'message': message
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'filename': filename,
            'src_dir': src_dirname,
            'message': f"エラー: {src_dirname}/{filename} の処理に失敗しました ({str(e)})"
        }

@app.route('/api/arrange', methods=['POST'])
def arrange():
    global is_cancelled
    is_cancelled = False
    
    data = request.json
    src_dirs = data.get('src_dirs')
    dst_dir = data.get('dst_dir')
    naming_rule = data.get('naming_rule', 'YYYY-MM-DD')
    mode = data.get('mode', 'copy') # 'copy' or 'move'
    dry_run = data.get('dry_run', False) # シミュレーションモード

    if not src_dirs and data.get('src_dir'):
        src_dirs = [data.get('src_dir')]

    if not src_dirs or not dst_dir:
        return jsonify({'error': 'コピー元とコピー先のディレクトリを指定してください。'}), 400

    src_dirs = [d.strip() for d in src_dirs if d and d.strip()]
    if not src_dirs:
        return jsonify({'error': 'コピー元ディレクトリを指定してください。'}), 400

    for d in src_dirs:
        if not os.path.isdir(d):
            return jsonify({'error': f'コピー元ディレクトリが存在しません: {d}'}), 400
    if not os.path.isdir(dst_dir):
        return jsonify({'error': 'コピー先ディレクトリが存在しません。'}), 400

    # 命名規則
    rule_mapping = {
        'YYYY-MM-DD': '%Y-%m-%d',
        'YYYY/MM/DD': '%Y/%m/%d',
        'YYYY/MM': '%Y/%m',
        'YYYYMMDD': '%Y%m%d',
        'YYYY-MM': '%Y-%m',
        'YYYY': '%Y'
    }
    date_format = rule_mapping.get(naming_rule, '%Y-%m-%d')

    def generate():
        global is_cancelled
        files_to_process = []
        for d in src_dirs:
            try:
                dir_files = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
                dir_files = [f for f in dir_files if not f.startswith('.')]
                for f in dir_files:
                    files_to_process.append((d, f))
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'message': f'スキャンエラー ({d}): {str(e)}'}, ensure_ascii=False)}\n\n"
                return

        total_files = len(files_to_process)
        if total_files == 0:
            yield f"data: {json.dumps({'status': 'completed', 'message': '処理対象ファイルがありません。', 'progress': 100}, ensure_ascii=False)}\n\n"
            return

        copied_count = 0
        skipped_count = 0
        error_count = 0
        
        # ディスクI/O重視のため最大4スレッド、Dry Runは8スレッド
        max_workers = 8 if dry_run else 4
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_file_task, s_dir, filename, dst_dir, date_format, mode, dry_run): (s_dir, filename)
                for s_dir, filename in files_to_process
            }
            
            for idx, future in enumerate(as_completed(futures)):
                if is_cancelled:
                    yield f"data: {json.dumps({'status': 'cancelled', 'message': 'ユーザーによって処理がキャンセルされました。'}, ensure_ascii=False)}\n\n"
                    # 未実行タスクのキャンセル試行
                    for f in futures:
                        f.cancel()
                    return
                    
                res = future.result()
                
                if res['status'] == 'success':
                    act = res['action']
                    if act in ('copy', 'move', 'rename', 'rename_move'):
                        copied_count += 1
                    elif act == 'skip':
                        skipped_count += 1
                    elif act == 'error':
                        error_count += 1
                else:
                    error_count += 1
                    
                progress = int((idx + 1) / total_files * 100)
                
                yield f"data: {json.dumps({
                    'status': 'processing',
                    'current_file': f"{res.get('src_dir')}/{res.get('filename')}",
                    'copied': res.get('copied', False),
                    'action': res.get('action'),
                    'progress': progress,
                    'message': res.get('message'),
                    'stats': {
                        'total': total_files,
                        'copied': copied_count,
                        'skipped': skipped_count,
                        'errors': error_count
                    }
                }, ensure_ascii=False)}\n\n"

        status_text = 'シミュレーション完了' if dry_run else '処理完了'
        yield f"data: {json.dumps({
            'status': 'completed',
            'message': f'{status_text}: 合計 {total_files} 件 (完了/予定: {copied_count} 件, スキップ: {skipped_count} 件, エラー: {error_count} 件)',
            'progress': 100
        }, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)
