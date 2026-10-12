"""JSON API endpoints for health check, person registration, and real-time face recognition."""
import base64
import platform
from datetime import datetime, timezone

import cv2
import numpy as np
from flask import Blueprint, current_app, jsonify, request, send_file

from app.services.expressions import ModelNotLoadedError as FERModelNotLoadedError
from app.services.face_detector import ModelNotLoadedError
from app.services.person_service import PersonService
from app.services.recognition_service import RecognitionService
from app.validators import (
    ValidationError,
    validate_consent,
    validate_image_file,
    validate_person_name,
)

api_bp = Blueprint("api", __name__)


def _error_response(message: str, code: int = 400):
    return jsonify({"status": "error", "error": {"code": code, "message": message}}), code


@api_bp.get("/health")
def health():
    """Health check endpoint reporting system status and Phase 6 capabilities."""
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
                "face_detection": True,
                "face_recognition": True,
                "expression_analysis": True,
                "speech_feedback": True,
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
    except ValidationError as exc:
        return _error_response(str(exc), 400)
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
    """Replace an existing person's facial image and regenerate embeddings."""
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
    except ValidationError as exc:
        return _error_response(str(exc), 400)
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
    """Delete a person, associated facial images, and feature embeddings."""
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


@api_bp.post("/recognize")
def recognize():
    """Detect faces and match against registered persons from an image or video frame."""
    raw_bytes = None

    if request.is_json:
        data = request.get_json(silent=True) or {}
        img_data = data.get("image")
        if not img_data:
            return _error_response("No image provided in JSON request.", 400)
        # Strip data URL prefix if present (e.g. data:image/jpeg;base64,...)
        if "," in img_data:
            img_data = img_data.split(",", 1)[1]
        try:
            raw_bytes = base64.b64decode(img_data)
        except Exception:
            return _error_response("Invalid base64 image data.", 400)
    elif "image" in request.files:
        raw_bytes = request.files["image"].read()
    else:
        return _error_response("Image file (multipart) or base64 image (JSON) is required.", 400)

    if not raw_bytes:
        return _error_response("Uploaded image payload is empty.", 400)

    nparr = np.frombuffer(raw_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return _error_response("The provided image could not be decoded for processing.", 400)

    try:
        result = RecognitionService.recognize_faces(img_bgr)
        return jsonify(result), 200
    except (ModelNotLoadedError, FERModelNotLoadedError) as err:
        return _error_response(str(err), 503)
    except Exception as exc:
        current_app.logger.exception("Unexpected error during face recognition: %s", exc)
        return _error_response("Internal error during face recognition processing.", 500)
