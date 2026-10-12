"""Application factory for AI Person Recognition."""
from flask import Flask

from .config import Config
from .db import init_app as init_db_app
from .errors import register_error_handlers
from .routes import register_blueprints
from .security import register_security_headers


def create_app(config_object=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.json.sort_keys = False  # keep response fields in a readable order

    init_db_app(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_security_headers(app)
    return app

