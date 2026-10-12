"""Application configuration with safe defaults.

Values come from environment variables (optionally loaded from a local .env
file). Defaults are safe: debug off, bound to localhost only, random secret key.
"""
import os
import secrets

# Load a local .env file (if present) before any setting is read.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional at runtime
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(int(default))).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    APP_NAME = "AI Person Recognition"
    APP_VERSION = "0.3.0"
    PHASE = 3

    # A missing SECRET_KEY must never fall back to a hardcoded value.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = _env_int("PORT", 5000)
    DEBUG = _env_bool("FLASK_DEBUG", False)
    TESTING = False

    # Base data directory outside static/ for privacy
    _BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(_BASE_DIR, "data")
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or os.path.join(DATA_DIR, "app.db")
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR") or os.path.join(DATA_DIR, "faces")

    # Local AI Model Configuration (OpenCV Zoo YuNet and SFace)
    MODELS_DIR = os.environ.get("MODELS_DIR") or os.path.join(_BASE_DIR, "models")
    YUNET_MODEL_PATH = os.environ.get("YUNET_MODEL_PATH") or os.path.join(
        MODELS_DIR, "face_detection_yunet_2023mar.onnx"
    )
    SFACE_MODEL_PATH = os.environ.get("SFACE_MODEL_PATH") or os.path.join(
        MODELS_DIR, "face_recognition_sface_2021dec.onnx"
    )

    # Detection and Matching Thresholds
    YUNET_SCORE_THRESHOLD = _env_float("YUNET_SCORE_THRESHOLD", 0.6)
    YUNET_NMS_THRESHOLD = _env_float("YUNET_NMS_THRESHOLD", 0.3)
    RECOGNITION_COSINE_THRESHOLD = _env_float("RECOGNITION_COSINE_THRESHOLD", 0.363)
    RECOGNITION_UNCERTAIN_LOWER = _env_float("RECOGNITION_UNCERTAIN_LOWER", 0.30)

    # Image upload restrictions
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max request size
    MAX_IMAGE_SIZE_BYTES = _env_int("MAX_IMAGE_SIZE_BYTES", 5 * 1024 * 1024)
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-only-secret-key"

