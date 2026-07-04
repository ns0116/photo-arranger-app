import logging
import os
import socket
import sys
import threading
import time
import webbrowser

from flask import Flask

from config import Config, setup_logging


def create_app(config_class=Config):
    """Application factory to create and configure the Flask app instance."""
    # Handle PyInstaller packaging paths for templates/static files
    if getattr(sys, "frozen", False):
        template_folder = os.path.join(sys._MEIPASS, "templates")
        static_folder = os.path.join(sys._MEIPASS, "static")
        app = Flask(
            __name__, template_folder=template_folder, static_folder=static_folder
        )
    else:
        app = Flask(__name__)

    # Setup structured logging
    setup_logging(app)

    # Initialize SQLite database
    from services.db_service import initialize_db

    initialize_db()

    # Initialize routes blueprints
    from routes import init_routes

    init_routes(app)

    return app


if __name__ == "__main__":
    from utils.platform_utils import find_free_port

    # Create the Flask application instance
    app = create_app()

    # Find an available port
    free_port = find_free_port(Config.DEFAULT_PORT, Config.MAX_PORT)

    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://127.0.0.1:{free_port}")

    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        threading.Thread(target=open_browser, daemon=True).start()

    logging.info(f"Starting server at http://127.0.0.1:{free_port}")
    app.run(host="127.0.0.1", port=free_port, debug=not is_frozen)
