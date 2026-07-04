import logging
import platform
import socket
import subprocess


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

        else:
            raise NotImplementedError("Unsupported OS for folder selection dialog.")
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
