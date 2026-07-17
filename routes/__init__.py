from routes.arrange import arrange_bp
from routes.directories import directories_bp
from routes.report import report_bp
from routes.system import system_bp
from routes.thumbnail import thumbnail_bp


def init_routes(app):
    """Registers all Flask blueprints to the application."""
    app.register_blueprint(system_bp)
    app.register_blueprint(arrange_bp)
    app.register_blueprint(directories_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(thumbnail_bp)
