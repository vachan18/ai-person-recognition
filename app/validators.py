"""Input validation for person profile data and facial image uploads."""
import io
from typing import Any, Dict, Set, Tuple
from PIL import Image, UnidentifiedImageError


class ValidationError(ValueError):
    """Raised when user input or uploaded file fails validation."""
    pass


def validate_person_name(name: Any) -> str:
    """Validate and sanitize a person's name.

    Ensures the name is a non-empty string within acceptable length.
    """
    if not isinstance(name, str):
        raise ValidationError("Person name must be a string.")
    
    cleaned = name.strip()
    if not cleaned:
        raise ValidationError("Person name is required and cannot be empty.")
    
    if len(cleaned) > 100:
        raise ValidationError("Person name must not exceed 100 characters.")
    
    return cleaned


def validate_consent(consent: Any) -> bool:
    """Validate that the user provided explicit biometric consent."""
    if isinstance(consent, bool):
        if not consent:
            raise ValidationError("Biometric consent is required before storing facial images.")
        return True
    
    if isinstance(consent, str):
        val = consent.strip().lower()
        if val in {"true", "1", "yes", "on"}:
            return True

    raise ValidationError("Biometric consent is required before storing facial images.")


def validate_image_file(
    file_storage: Any,
    max_size_bytes: int = 5 * 1024 * 1024,
    allowed_extensions: Set[str] = None
) -> Tuple[bytes, str, Dict[str, Any]]:
    """Validate an uploaded image file for format, integrity, and dimensions.

    Returns:
        (image_bytes, extension, metadata_dict)
    """
    if allowed_extensions is None:
        allowed_extensions = {"jpg", "jpeg", "png", "webp"}

    if file_storage is None:
        raise ValidationError("An image file is required.")

    filename = getattr(file_storage, "filename", "") or ""
    if not filename.strip():
        raise ValidationError("An image file is required.")

    # Check extension
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        raise ValidationError(
            f"Image file must have a valid extension ({', '.join(sorted(allowed_extensions))})."
        )
    ext = parts[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Unsupported file extension '.{ext}'. Supported extensions: {', '.join(sorted(allowed_extensions))}."
        )

    # Read data safely
    file_storage.seek(0)
    data = file_storage.read()

    if not data:
        raise ValidationError("Uploaded image file is empty.")

    if len(data) > max_size_bytes:
        limit_mb = max_size_bytes // (1024 * 1024)
        raise ValidationError(f"Image exceeds the maximum allowed size of {limit_mb} MB.")

    # Verify decodability and integrity with Pillow
    try:
        # First pass: verify header and integrity
        bio = io.BytesIO(data)
        with Image.open(bio) as img:
            img.verify()
        
        # Second pass: read format and dimensions (verify() closes/invalidates the image object)
        bio = io.BytesIO(data)
        with Image.open(bio) as img:
            fmt = (img.format or "").upper()
            width, height = img.size

            allowed_formats = {"JPEG", "PNG", "WEBP"}
            if fmt not in allowed_formats:
                raise ValidationError(
                    f"Unsupported image format '{fmt}'. Decoded image must be JPEG, PNG, or WEBP."
                )

            if width < 20 or height < 20:
                raise ValidationError("Image dimensions are too small (minimum 20x20 pixels).")

            metadata = {
                "format": fmt,
                "width": width,
                "height": height,
                "size_bytes": len(data),
            }

            # Map extension standard
            canonical_ext = "jpg" if fmt == "JPEG" else fmt.lower()

            return data, canonical_ext, metadata

    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValidationError("Uploaded file is corrupt or not a valid, decodable image.") from exc
