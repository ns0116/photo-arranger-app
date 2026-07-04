import logging
import os
import sys


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

    # Rename attempts limit for name collisions
    MAX_RENAME_ATTEMPTS = 10000

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
