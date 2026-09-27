import logging
import os
import threading
import time
from datetime import datetime

from config import Config
from services.photo_service import (
    _arrange_photos_stream,
    arrange_execution_lock,
    scan_directories,
)


class FolderWatcher:
    """Monitors configured source directories periodically and triggers automatic photo arrangement."""

    def __init__(self):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._running = False
        self._status = "stopped"  # "stopped", "idle", "arranging"
        self._config = {}
        self._last_run = None
        self._last_count = 0
        self._last_error = None
        # Track file stability: filepath -> (size, mtime, stable_ticks)
        self._file_snapshots = {}

    def get_status(self):
        """Returns the current watcher status and metadata."""
        with self._lock:
            return {
                "running": self._running,
                "status": self._status,
                "last_run": self._last_run,
                "last_count": self._last_count,
                "last_error": self._last_error,
                "config": {
                    "src_dirs": self._config.get("src_dirs", []),
                    "dst_dir": self._config.get("dst_dir", ""),
                    "interval": self._config.get("interval", 30),
                    "mode": self._config.get("mode", "copy"),
                    "naming_rule": self._config.get("naming_rule", "YYYY-MM-DD"),
                },
            }

    def start(self, config):
        """Starts the folder watcher daemon thread.

        config expects:
            - src_dirs: list[str]
            - dst_dir: str
            - interval: int (seconds, default 30, min 5)
            - mode: str ('copy' or 'move', default 'copy')
            - naming_rule: str
            - rules: list[dict] (optional)
            - extensions: list[str] (optional)
            - recursive: bool (optional)
        """
        with self._lock:
            if self._running:
                return False, "Watcher is already running."

            src_dirs = [
                d.strip() for d in config.get("src_dirs", []) if d and d.strip()
            ]
            dst_dir = (config.get("dst_dir") or "").strip()

            if not src_dirs or not dst_dir:
                return False, "Source and destination directories are required."

            for d in src_dirs:
                if not os.path.isdir(d):
                    return False, f"Source directory does not exist: {d}"

            if not os.path.isdir(dst_dir):
                return False, f"Destination directory does not exist: {dst_dir}"

            interval = max(5, int(config.get("interval", 30)))
            self._config = {
                "src_dirs": src_dirs,
                "dst_dir": dst_dir,
                "interval": interval,
                "mode": config.get("mode", "copy"),
                "naming_rule": config.get("naming_rule", "YYYY-MM-DD"),
                "rules": config.get("rules", []),
                "extensions": config.get("extensions"),
                "recursive": bool(config.get("recursive", False)),
            }

            self._stop_event.clear()
            self._running = True
            self._status = "idle"
            self._last_error = None
            self._file_snapshots = {}

            self._thread = threading.Thread(
                target=self._worker_loop, name="FolderWatcherThread", daemon=True
            )
            self._thread.start()
            logging.info(
                f"Folder watcher started. Interval: {interval}s, Sources: {src_dirs}, Target: {dst_dir}"
            )
            return True, "Watcher started successfully."

    def stop(self):
        """Stops the folder watcher daemon thread."""
        with self._lock:
            if not self._running:
                return True, "Watcher is already stopped."

            self._running = False
            self._status = "stopped"
            self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        logging.info("Folder watcher stopped.")
        return True, "Watcher stopped successfully."

    def _worker_loop(self):
        """Background monitoring loop."""
        interval = self._config.get("interval", 30)

        while not self._stop_event.is_set():
            # Wait for next cycle or until stopped
            if self._stop_event.wait(timeout=interval):
                break

            try:
                self._check_and_arrange()
            except Exception as e:
                logging.error(f"Error during folder watcher cycle: {e}")
                with self._lock:
                    self._last_error = str(e)
                    self._status = "idle"

    def _check_and_arrange(self):
        """Scans directories and triggers arrange_photos if new stable files are detected."""
        src_dirs = self._config.get("src_dirs", [])
        dst_dir = self._config.get("dst_dir")
        extensions = self._config.get("extensions")
        recursive = self._config.get("recursive", False)

        try:
            candidates = scan_directories(
                src_dirs, extensions=extensions, recursive=recursive
            )
        except Exception as e:
            logging.warning(f"Watcher scan error: {e}")
            return

        if not candidates:
            return

        # Check stability: file must have identical size/mtime across 2 checks
        # to ensure it's not mid-write / copy.
        current_stable = []
        new_snapshots = {}

        for s_dir, fname in candidates:
            fpath = os.path.join(s_dir, fname)
            try:
                stat = os.stat(fpath)
                curr_sig = (stat.st_size, stat.st_mtime)
                prev_sig = self._file_snapshots.get(fpath)

                if prev_sig == curr_sig:
                    current_stable.append((s_dir, fname))
                new_snapshots[fpath] = curr_sig
            except OSError:
                continue

        self._file_snapshots = new_snapshots

        if not current_stable:
            return

        # Attempt to acquire arrange_execution_lock without blocking (non-intrusive)
        acquired = arrange_execution_lock.acquire(blocking=False)
        if not acquired:
            logging.info("Watcher: Another arrangement is in progress. Skipping cycle.")
            return

        try:
            with self._lock:
                self._status = "arranging"

            logging.info(
                f"Watcher: Starting auto-arrangement for {len(current_stable)} candidates..."
            )
            generator = _arrange_photos_stream(
                src_dirs=src_dirs,
                dst_dir=dst_dir,
                naming_rule=self._config.get("naming_rule", "YYYY-MM-DD"),
                mode=self._config.get("mode", "copy"),
                dry_run=False,
                extensions=extensions,
                recursive=recursive,
                rules=self._config.get("rules"),
            )

            # Consume SSE stream to drive processing
            processed_count = 0
            for chunk in generator:
                # Track if files were copied/moved
                if (
                    '"action": "copy"' in chunk
                    or '"action": "move"' in chunk
                    or '"action": "rename"' in chunk
                ):
                    processed_count += 1

            with self._lock:
                self._last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._last_count = processed_count
                self._last_error = None
                logging.info(
                    f"Watcher: Auto-arrangement finished. Processed {processed_count} files."
                )

        except Exception as e:
            logging.error(f"Watcher execution error: {e}")
            with self._lock:
                self._last_error = str(e)
        finally:
            with self._lock:
                if self._running:
                    self._status = "idle"
            arrange_execution_lock.release()


# Global singleton watcher instance
folder_watcher = FolderWatcher()
