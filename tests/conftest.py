import os

import pytest
from PIL import Image

from app import create_app
from config import Config

# Overwrite log dir/file during tests to avoid writing to user's home directory
Config.LOG_DIR = os.path.join(os.path.dirname(__file__), "../.pytest_cache/logs")
Config.LOG_FILE = os.path.join(Config.LOG_DIR, "test_app.log")
Config.DB_FILE = os.path.join(Config.LOG_DIR, "test_history.db")


@pytest.fixture(autouse=True)
def clean_database():
    """Ensures each test runs with a fresh, empty SQLite database."""
    if os.path.exists(Config.DB_FILE):
        try:
            os.remove(Config.DB_FILE)
        except Exception:
            pass

    from services.db_service import initialize_db

    initialize_db()


@pytest.fixture
def app():
    """Provides a test instance of the Flask application."""
    flask_app = create_app()
    flask_app.config.update(
        {
            "TESTING": True,
        }
    )
    return flask_app


@pytest.fixture
def client(app):
    """Provides a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def temp_workspace(tmp_path):
    """Provides temporary source and destination directories for tests."""
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()
    return {"src": str(src_dir), "dst": str(dst_dir), "root": str(tmp_path)}


@pytest.fixture
def image_creator():
    """Provides a helper function to create dummy image or text files for testing."""

    def _create(path, exif_date_str=None, content=None):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if content is not None:
            # Write a plain file (like a text file or custom binary data)
            with open(path, "wb") as f:
                f.write(content)
        else:
            # Write a dummy image using Pillow
            img = Image.new("RGB", (5, 5), color="blue")
            if exif_date_str:
                exif = img.getexif()
                # 36867: DateTimeOriginal, 36868: DateTimeDigitized, 306: DateTime
                exif[36867] = exif_date_str
                exif[36868] = exif_date_str
                exif[306] = exif_date_str
                img.save(path, "JPEG", exif=exif)
            else:
                img.save(path, "JPEG")

    return _create
