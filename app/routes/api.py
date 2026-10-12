"""JSON API endpoints for health check, person registration, and profile management."""
import platform
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, send_file

from app.services.person_service import PersonService
from app.validators import ValidationError, validate_consent, validate_image_file, validate_person_name

api_bp = Blueprint("api", __name__)


def _error_response(message: str, code: int = 400):
    return jsonify({"status": "error", "error": {"code": code, "message": message}}), code


@api_bp.get("/health")
def health():
    """Health check endpoint reporting system status and Phase 2 capabilities."""
    return jsonify(
        {
            "status": "ok",
            "app": current_app.config["APP_NAME"],
            "version": current_app.config["APP_VERSION"],
            "phase": current_app.config["PHASE"],
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "python": platform.python_version(),
            "capabilities": {
                "camera_preview": True,
                "face_detection": False,
                "face_recognition": False,
                "expression_analysis": False,
                "speech_feedback": False,
                "database": True,
            },
        }
    )


@api_bp.get("/persons")
def list_persons():
    """List registered people with optional ?q= search filtering."""
    query = request.args.get("q", "").strip()
    persons = PersonService.list_persons(query if query else None)
    return jsonify({"status": "ok", "count": len(persons), "persons": persons})


@api_bp.post("/persons")
def create_person():
    """Register a new person with name, biometric consent, and facial image."""
    name_raw = request.form.get("name")
    consent_raw = request.form.get("consent")
    file_storage = request.files.get("image")

    try:
        name = validate_person_name(name_raw)
        validate_consent(consent_raw)
        max_size = current_app.config.get("MAX_IMAGE_SIZE_BYTES", 5 * 1024 * 1024)
        allowed_exts = current_app.config.get(
            "ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png", "webp"}
        )
        img_bytes, ext, metadata = validate_image_file(file_storage, max_size, allowed_exts)
    except ValidationError as exc:
        return _error_response(str(exc), 400)

    try:
        person = PersonService.create_person(name, img_bytes, ext, metadata)
    except Exception:
        current_app.logger.exception("Unexpected error during person creation.")
        return _error_response("Could not save person profile. Please try again.", 500)

    return (
        jsonify({"status": "ok", "message": "Person registered successfully.", "person": person}),
        201,
    )


@api_bp.get("/persons/<int:person_id>")
def get_person(person_id: int):
    """Retrieve a single person's profile."""
    person = PersonService.get_person(person_id)
    if not person:
        return _error_response("Person not found.", 404)
    return jsonify({"status": "ok", "person": person})


@api_bp.put("/persons/<int:person_id>")
def update_person(person_id: int):
    """Update a person's name."""
    if request.is_json:
        data = request.get_json(silent=True) or {}
        name_raw = data.get("name")
    else:
        name_raw = request.form.get("name")

    try:
        name = validate_person_name(name_raw)
    except ValidationError as exc:
        return _error_response(str(exc), 400)

    person = PersonService.update_person_name(person_id, name)
    if not person:
        return _error_response("Person not found.", 404)

    return jsonify({"status": "ok", "message": "Person updated successfully.", "person": person})


@api_bp.post("/persons/<int:person_id>/image")
def replace_person_image(person_id: int):
    """Replace an existing person's facial image."""
    # Ensure person exists first
    existing = PersonService.get_person(person_id)
    if not existing:
        return _error_response("Person not found.", 404)

    file_storage = request.files.get("image")
    try:
        max_size = current_app.config.get("MAX_IMAGE_SIZE_BYTES", 5 * 1024 * 1024)
        allowed_exts = current_app.config.get(
            "ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png", "webp"}
        )
        img_bytes, ext, metadata = validate_image_file(file_storage, max_size, allowed_exts)
    except ValidationError as exc:
        return _error_response(str(exc), 400)

    try:
        person = PersonService.replace_person_image(person_id, img_bytes, ext, metadata)
    except Exception:
        current_app.logger.exception("Unexpected error during image replacement.")
        return _error_response("Could not update facial image. Please try again.", 500)

    if not person:
        return _error_response("Person not found.", 404)

    return jsonify(
        {"status": "ok", "message": "Facial image updated successfully.", "person": person}
    )


@api_bp.delete("/persons/<int:person_id>")
def delete_person(person_id: int):
    """Delete a person and associated facial image files."""
    deleted = PersonService.delete_person(person_id)
    if not deleted:
        return _error_response("Person not found.", 404)

    return jsonify({"status": "ok", "message": "Person deleted successfully."})


@api_bp.get("/persons/<int:person_id>/image")
def get_person_image(person_id: int):
    """Serve a person's registered facial image safely through an application route."""
    file_info = PersonService.get_person_image_file(person_id)
    if not file_info:
        return _error_response("Image not found.", 404)

    full_path, mime_type = file_info
    resp = send_file(full_path, mimetype=mime_type, max_age=0)
    resp.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
