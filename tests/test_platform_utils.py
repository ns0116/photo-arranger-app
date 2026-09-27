import subprocess
from unittest.mock import MagicMock, patch

import pytest

from utils.platform_utils import (
    _select_dir_dialog_linux,
    find_free_port,
    select_dir_dialog,
)


def test_find_free_port():
    port = find_free_port(start_port=10000, max_port=20000)
    assert 10000 <= port <= 20000


def test_select_dir_dialog_darwin_success():
    with patch("platform.system", return_value="Darwin"):
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("/Users/test/Photos\n", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            result = select_dir_dialog()
            assert result == "/Users/test/Photos"


def test_select_dir_dialog_darwin_timeout():
    with patch("platform.system", return_value="Darwin"):
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.side_effect = [
                subprocess.TimeoutExpired(cmd="osascript", timeout=120),
                ("", ""),
            ]
            mock_popen.return_value = mock_proc

            result = select_dir_dialog()
            assert result == ""
            mock_proc.kill.assert_called_once()


def test_select_dir_dialog_windows_success():
    with patch("platform.system", return_value="Windows"):
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("C:\\Photos\r\n", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            result = select_dir_dialog()
            assert result == "C:\\Photos"


def test_select_dir_dialog_linux_zenity():
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: (
                "/usr/bin/zenity" if cmd == "zenity" else None
            )
            with patch("subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                mock_proc.communicate.return_value = ("/home/user/photos\n", "")
                mock_proc.returncode = 0
                mock_popen.return_value = mock_proc

                result = select_dir_dialog()
                assert result == "/home/user/photos"


def test_select_dir_dialog_linux_kdialog():
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: (
                "/usr/bin/kdialog" if cmd == "kdialog" else None
            )
            with patch("subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                mock_proc.communicate.return_value = ("/home/user/kde_photos\n", "")
                mock_proc.returncode = 0
                mock_popen.return_value = mock_proc

                result = select_dir_dialog()
                assert result == "/home/user/kde_photos"


def test_select_dir_dialog_linux_tkinter():
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which", return_value=None):
            with patch.dict("os.environ", {"DISPLAY": ":0"}):
                mock_tk_module = MagicMock()
                mock_filedialog = MagicMock()
                mock_filedialog.askdirectory.return_value = "/home/user/tk_photos"
                mock_tk_module.filedialog = mock_filedialog

                with patch.dict(
                    "sys.modules",
                    {
                        "tkinter": mock_tk_module,
                        "tkinter.filedialog": mock_filedialog,
                    },
                ):
                    result = _select_dir_dialog_linux()
                    assert result == "/home/user/tk_photos"


def test_select_dir_dialog_linux_no_gui_raises():
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                with pytest.raises(NotImplementedError) as exc_info:
                    select_dir_dialog()
                assert "GUIダイアログツール" in str(exc_info.value)


def test_select_dir_dialog_unsupported_os_raises():
    with patch("platform.system", return_value="FreeBSD"):
        with pytest.raises(NotImplementedError) as exc_info:
            select_dir_dialog()
        assert "Unsupported OS" in str(exc_info.value)
