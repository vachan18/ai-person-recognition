"""Consistent error handling: JSON for /api/*, a friendly HTML page elsewhere."""
import logging

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)

_MESSAGES = {
    400: "The request could not be understood.",
    404: "The page or resource you asked for was not found.",
    405: "That method is not allowed for this address.",
    413: "The request is too large.",
    500: "Something went wrong on the server. Please try again.",
}


def _wants_json() -> bool:
    return request.path.startswith("/api/")


def _respond(status: int, name: str):
    message = _MESSAGES.get(status, name)
    if _wants_json():
        return jsonify({"status": "error", "error": {"code": status, "name": name, "message": message}}), status
    return render_template("error.html", code=status, name=name, message=message, active=None), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        return _respond(exc.code or 500, exc.name)

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        # Log details server-side only; never expose internals to the client.
        log.exception("Unhandled error: %s", exc)
        return _respond(500, "Internal Server Error")
