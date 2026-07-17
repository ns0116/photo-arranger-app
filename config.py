import logging
import os
import sys
from datetime import datetime


class Config:
    # Image extensions for EXIF processing
    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".tif",
        ".heic",
        ".heif",
        ".webp",
        ".bmp",
    }

    # Video extensions. Pillow cannot read EXIF from these, so date resolution
    # always falls back to file mtime (see utils.date_utils.get_exif_date, which
    # only attempts EXIF extraction for IMAGE_EXTENSIONS). Accurate capture-date
    # extraction from video container metadata (e.g. MP4 mvhd/moov atoms) is a
    # documented follow-up, not implemented here (see issue #26).
    VIDEO_EXTENSIONS = {
        ".mp4",
        ".m4v",
        ".mov",
        ".avi",
    }

    # Combined set of all media extensions scanned/processed by default.
    MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

    # Rename attempts limit for name collisions
    MAX_RENAME_ATTEMPTS = 10000

    # EXIF sanity-check thresholds (Dry Run pre-flight warnings — see issue #32).
    # Any resolved date-taken older than this is considered implausible (also
    # catches the common "epoch" bug of 1970-01-01 from bad EXIF/camera clocks).
    EXIF_MIN_VALID_DATE = datetime(1980, 1, 1)
    # Dates further in the future than this many minutes are treated as
    # abnormal, allowing a small buffer for clock skew between machines.
    EXIF_FUTURE_TOLERANCE_MINUTES = 5

    # Date rules configuration
    NAMING_RULES = {
        "YYYY-MM-DD": "%Y-%m-%d",
        "YYYY/MM/DD": "%Y/%m/%d",
        "YYYY/MM": "%Y/%m",
        "YYYYMMDD": "%Y%m%d",
        "YYYY-MM": "%Y-%m",
        "YYYY": "%Y",
    }

    # Threading defaults based on CPU cores
    CPU_CORES = os.cpu_count() or 4
    MAX_WORKERS_DRYRUN = CPU_CORES * 2
    MAX_WORKERS_ARRANGE = max(1, CPU_CORES // 2)  # Disk I/O bound

    # Port configuration
    DEFAULT_PORT = 5001
    MAX_PORT = 9999

    # Logging configuration
    LOG_DIR = os.path.expanduser("~/.photo-arranger")
    LOG_FILE = os.path.join(LOG_DIR, "app.log")
    DB_FILE = os.path.join(LOG_DIR, "history.db")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


def setup_logging(app=None):
    """Initializes structured logging to stdout and the application log file."""
    # Ensure log directory exists
    try:
        os.makedirs(Config.LOG_DIR, exist_ok=True)
    except Exception as e:
        sys.stderr.write(
            f"Warning: Could not create log directory {Config.LOG_DIR}: {e}\n"
        )

    # Determine numeric log level
    numeric_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    # Define formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d): %(message)s"
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Stream Handler (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # File Handler
    try:
        file_handler = logging.FileHandler(Config.LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"Warning: Could not configure file logger: {e}\n")

    # Silence third-party logs (like Werkzeug requests unless warning/error)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # Log startup info
    logging.info(
        f"Logging initialized. Level: {Config.LOG_LEVEL}, File: {Config.LOG_FILE}"
    )
