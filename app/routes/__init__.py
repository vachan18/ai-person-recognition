"""Route modules. Add new blueprints here as later phases introduce them."""
from flask import Flask

from .api import api_bp
from .pages import pages_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
