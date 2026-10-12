"""Unit tests for input validators (name, consent, image file decodability)."""
import io
from PIL import Image
import pytest
from werkzeug.datastructures import FileStorage

from app.validators import (
    ValidationError,
    validate_consent,
    validate_image_file,
    validate_person_name,
)


def test_validate_person_name_success():
    assert validate_person_name("Alice Smith") == "Alice Smith"
    assert validate_person_name("  Bob Jones  ") == "Bob Jones"


@pytest.mark.parametrize(
    "invalid_name",
    ["", "   ", None, 123, []],
)
def test_validate_person_name_rejects_empty(invalid_name):
    with pytest.raises(ValidationError):
        validate_person_name(invalid_name)


def test_validate_person_name_rejects_too_long():
    long_name = "A" * 101
    with pytest.raises(ValidationError) as exc:
        validate_person_name(long_name)
    assert "100 characters" in str(exc.value)


@pytest.mark.parametrize("valid_consent", [True, "true", "True", "1", "yes", "on"])
def test_validate_consent_valid(valid_consent):
    assert validate_consent(valid_consent) is True


@pytest.mark.parametrize("invalid_consent", [False, "false", "0", "no", None, "", "other"])
def test_validate_consent_invalid(invalid_consent):
    with pytest.raises(ValidationError) as exc:
        validate_consent(invalid_consent)
    assert "consent is required" in str(exc.value).lower()


def test_validate_image_file_valid_jpeg(sample_image_bytes):
    fs = FileStorage(
        stream=io.BytesIO(sample_image_bytes),
        filename="portrait.jpg",
        content_type="image/jpeg",
    )
    data, ext, meta = validate_image_file(fs)
    assert ext == "jpg"
    assert meta["format"] == "JPEG"
    assert meta["width"] == 100
    assert meta["height"] == 100
    assert len(data) == len(sample_image_bytes)


def test_validate_image_file_valid_png(sample_png_bytes):
    fs = FileStorage(
        stream=io.BytesIO(sample_png_bytes),
        filename="face.png",
        content_type="image/png",
    )
    data, ext, meta = validate_image_file(fs)
    assert ext == "png"
    assert meta["format"] == "PNG"
    assert meta["width"] == 80


def test_validate_image_file_valid_webp(sample_webp_bytes):
    fs = FileStorage(
        stream=io.BytesIO(sample_webp_bytes),
        filename="face.webp",
        content_type="image/webp",
    )
    data, ext, meta = validate_image_file(fs)
    assert ext == "webp"
    assert meta["format"] == "WEBP"


def test_validate_image_file_rejects_unsupported_extension(sample_image_bytes):
    fs = FileStorage(
        stream=io.BytesIO(sample_image_bytes),
        filename="face.gif",
        content_type="image/gif",
    )
    with pytest.raises(ValidationError) as exc:
        validate_image_file(fs)
    assert "Unsupported file extension" in str(exc.value)


def test_validate_image_file_rejects_empty():
    fs = FileStorage(
        stream=io.BytesIO(b""),
        filename="empty.jpg",
        content_type="image/jpeg",
    )
    with pytest.raises(ValidationError) as exc:
        validate_image_file(fs)
    assert "empty" in str(exc.value).lower()


def test_validate_image_file_rejects_corrupted_data():
    fs = FileStorage(
        stream=io.BytesIO(b"not an image file data here!"),
        filename="broken.jpg",
        content_type="image/jpeg",
    )
    with pytest.raises(ValidationError) as exc:
        validate_image_file(fs)
    assert "corrupt" in str(exc.value).lower() or "not a valid" in str(exc.value).lower()


def test_validate_image_file_rejects_too_small_dimensions():
    buf = io.BytesIO()
    img = Image.new("RGB", (10, 10))
    img.save(buf, format="JPEG")
    buf.seek(0)

    fs = FileStorage(
        stream=buf,
        filename="tiny.jpg",
        content_type="image/jpeg",
    )
    with pytest.raises(ValidationError) as exc:
        validate_image_file(fs)
    assert "too small" in str(exc.value).lower()


def test_validate_image_file_rejects_oversized(sample_image_bytes):
    fs = FileStorage(
        stream=io.BytesIO(sample_image_bytes),
        filename="large.jpg",
        content_type="image/jpeg",
    )
    with pytest.raises(ValidationError) as exc:
        validate_image_file(fs, max_size_bytes=100)  # max 100 bytes
    assert "exceeds the maximum" in str(exc.value).lower()
