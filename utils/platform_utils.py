import logging
import os
import platform
import shutil
import socket
import subprocess


def _select_dir_dialog_linux():
    """Linux native folder selection dialog with multi-tier fallback.

    Tries in order:
    1. zenity (GTK / GNOME standard)
    2. kdialog (Qt / KDE standard)
    3. tkinter (Python standard GUI fallback if graphical display is present)
    """
    # 1. Try zenity (GNOME / GTK standard)
    if shutil.which("zenity"):
        try:
            process = subprocess.Popen(
                [
                    "zenity",
                    "--file-selection",
                    "--directory",
                    "--title=フォルダを選択してください",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, _ = process.communicate(timeout=120)
                if process.returncode == 0:
                    return stdout.strip()
                return ""  # Cancelled or closed
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                return ""
        except Exception as e:
            logging.warning(f"zenity folder dialog failed: {e}")

    # 2. Try kdialog (KDE / Qt standard)
    if shutil.which("kdialog"):
        try:
            process = subprocess.Popen(
                [
                    "kdialog",
                    "--getexistingdirectory",
                    ".",
                    "--title",
                    "フォルダを選択してください",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, _ = process.communicate(timeout=120)
                if process.returncode == 0:
                    return stdout.strip()
                return ""  # Cancelled or closed
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                return ""
        except Exception as e:
            logging.warning(f"kdialog folder dialog failed: {e}")

    # 3. Fallback to tkinter if graphical display is available
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            try:
                root.attributes("-topmost", True)
            except Exception:
                pass
            selected = filedialog.askdirectory(title="フォルダを選択してください")
            root.destroy()
            return selected or ""
        except Exception as e:
            logging.warning(f"tkinter folder dialog fallback failed: {e}")

    raise NotImplementedError(
        "GUIダイアログツール（zenity, kdialog, または python3-tk）が見つかりません。手動でパスを入力してください。"
    )


def select_dir_dialog():
    """Opens a native platform folder select dialog with a timeout.

    Returns:
        str: Absolute path of the selected folder, or an empty string if cancelled.
    """
    system = platform.system()
    try:
        if system == "Darwin":
            # macOS native folder selection via AppleScript
            script = (
                'POSIX path of (choose folder with prompt "フォルダを選択してください")'
            )
            process = subprocess.Popen(
                ["osascript", "-e", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                return ""
            if process.returncode == 0:
                return stdout.strip()
            return ""

        elif system == "Windows":
            # Windows native folder selection via PowerShell Forms
            script = (
                "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$f.Description = 'フォルダを選択してください'; "
                "if($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $f.SelectedPath }"
            )
            process = subprocess.Popen(
                ["powershell", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                return ""
            if process.returncode == 0:
                return stdout.strip()
            return ""

        elif system == "Linux":
            # Linux native folder selection via zenity, kdialog, or tkinter fallback
            return _select_dir_dialog_linux()

        else:
            raise NotImplementedError(
                f"Unsupported OS for folder selection dialog: {system}"
            )
    except Exception as e:
        logging.error(f"Error in select_dir_dialog: {e}")
        raise e


def find_free_port(start_port=5001, max_port=9999):
    """Finds an available TCP port in the given range on localhost."""
    port = start_port
    while port <= max_port:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"No free ports found in range {start_port} to {max_port}.")
