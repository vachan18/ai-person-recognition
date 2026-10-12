import io
from PIL import Image
import pytest

from app import create_app
from app.config import TestingConfig


@pytest.fixture()
def app(tmp_path):
    """Create a test application instance with temporary database and uploads directory."""
    class IsolatedTestingConfig(TestingConfig):
        DATA_DIR = str(tmp_path / "data")
        DATABASE_PATH = str(tmp_path / "data" / "test.db")
        UPLOAD_DIR = str(tmp_path / "data" / "faces")

    return create_app(IsolatedTestingConfig)


@pytest.fixture()
def client(app):
    """Test client for HTTP requests."""
    return app.test_client()


@pytest.fixture()
def sample_image_bytes():
    """Generate a valid 100x100 RGB JPEG image in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(73, 109, 137))
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture()
def sample_png_bytes():
    """Generate a valid 80x80 RGBA PNG image in memory."""
    buf = io.BytesIO()
    img = Image.new("RGBA", (80, 80), color=(255, 120, 0, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def sample_webp_bytes():
    """Generate a valid 80x80 RGB WEBP image in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", (80, 80), color=(50, 150, 50))
    img.save(buf, format="WEBP")
    return buf.getvalue()


@pytest.fixture()
def sample_face_bytes():
    """Load a real valid portrait containing a detectable human face."""
    face_path = "tests/data/sample_face.jpg"
    with open(face_path, "rb") as f:
        return f.read()

