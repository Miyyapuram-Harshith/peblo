"""Artwork validation service using Pillow for server-side image inspection."""
import io
import json
from pathlib import Path

from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import ArtworkType

logger = get_logger("artwork")


class ArtworkValidationError(Exception):
    """Raised when artwork fails validation."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _load_artwork_specs() -> dict:
    """Load artwork specifications from reference.json."""
    settings = get_settings()
    ref_path = Path(settings.seed_data_path) / "reference.json"
    if ref_path.exists():
        ref = json.loads(ref_path.read_text())
        return ref.get("artwork", {})
    # Defaults
    return {
        "poster": {"aspect_ratio": "2:3", "width": 600, "height": 900, "max_size_bytes": 204800, "formats": ["image/jpeg", "image/png", "image/webp"]},
        "banner": {"aspect_ratio": "16:9", "width": 1280, "height": 720, "max_size_bytes": 204800, "formats": ["image/jpeg", "image/png", "image/webp"]},
        "thumbnail": {"aspect_ratio": "16:9", "width": 640, "height": 360, "max_size_bytes": 204800, "formats": ["image/jpeg", "image/png", "image/webp"]},
    }


PILLOW_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}

MIME_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _parse_aspect_ratio(ratio_str: str) -> tuple[int, int]:
    """Parse '2:3' into (2, 3)."""
    parts = ratio_str.split(":")
    return int(parts[0]), int(parts[1])


def validate_artwork(
    file_data: bytes,
    artwork_type: ArtworkType,
    original_filename: str | None = None,
) -> dict:
    """
    Validate image bytes against artwork specifications.

    Returns dict with: width, height, format, mime_type, size_bytes, sha256
    Raises ArtworkValidationError with human-readable messages on failure.
    """
    specs = _load_artwork_specs()
    type_key = artwork_type.value
    spec = specs.get(type_key)

    if not spec:
        raise ArtworkValidationError(
            code="ARTWORK_TYPE_UNKNOWN",
            message=f"Unknown artwork type: {type_key}",
        )

    size_bytes = len(file_data)
    max_size = spec.get("max_size_bytes", 204800)
    type_label = artwork_type.value.capitalize()

    # Size check first
    if size_bytes > max_size:
        size_kb = size_bytes / 1024
        max_kb = max_size / 1024
        raise ArtworkValidationError(
            code="ARTWORK_FILE_TOO_LARGE",
            message=f"This {type_label} is {size_kb:.0f} KB. {type_label} images must be {max_kb:.0f} KB or smaller. Please compress or resize the image.",
            details={"actual_bytes": size_bytes, "max_bytes": max_size, "actual_kb": round(size_kb, 1), "max_kb": round(max_kb, 1)},
        )

    # Try to open with Pillow - validates it's a real image
    try:
        img = Image.open(io.BytesIO(file_data))
        img.verify()  # Verify it's not corrupt
        # Re-open after verify (verify closes the stream)
        img = Image.open(io.BytesIO(file_data))
    except Exception:
        raise ArtworkValidationError(
            code="ARTWORK_CORRUPT",
            message=f"This file could not be read as a valid image. Please ensure you're uploading a JPEG, PNG, or WebP file.",
            details={"filename": original_filename},
        )

    # Format check - trust Pillow, not filename/Content-Type
    actual_format = img.format
    actual_mime = PILLOW_FORMAT_TO_MIME.get(actual_format, f"image/{actual_format.lower()}" if actual_format else "unknown")
    allowed_formats = spec.get("formats", ["image/jpeg", "image/png", "image/webp"])

    if actual_mime not in allowed_formats:
        raise ArtworkValidationError(
            code="ARTWORK_FORMAT_INVALID",
            message=f"This {type_label} is in {actual_format} format. Accepted formats are: {', '.join(f.split('/')[1].upper() for f in allowed_formats)}.",
            details={"actual_format": actual_format, "actual_mime": actual_mime, "allowed": allowed_formats},
        )

    # Dimension checks
    actual_width, actual_height = img.size
    expected_width = spec.get("width", 600)
    expected_height = spec.get("height", 900)
    tolerance = 0.10  # 10% tolerance

    width_min = int(expected_width * (1 - tolerance))
    width_max = int(expected_width * (1 + tolerance))
    height_min = int(expected_height * (1 - tolerance))
    height_max = int(expected_height * (1 + tolerance))

    if not (width_min <= actual_width <= width_max and height_min <= actual_height <= height_max):
        raise ArtworkValidationError(
            code="ARTWORK_DIMENSIONS_INVALID",
            message=f"This {type_label} is {actual_width} × {actual_height} pixels. {type_label} images should be approximately {expected_width} × {expected_height} pixels (±10%). Please resize the image.",
            details={
                "actual_width": actual_width,
                "actual_height": actual_height,
                "expected_width": expected_width,
                "expected_height": expected_height,
                "tolerance_percent": 10,
            },
        )

    # Aspect ratio check
    aspect_ratio_str = spec.get("aspect_ratio", "2:3")
    expected_ar_w, expected_ar_h = _parse_aspect_ratio(aspect_ratio_str)
    expected_ratio = expected_ar_w / expected_ar_h
    actual_ratio = actual_width / actual_height
    ratio_tolerance = 0.05  # 5% tolerance

    if abs(actual_ratio - expected_ratio) / expected_ratio > ratio_tolerance:
        actual_ar_str = f"{actual_width}:{actual_height}"
        raise ArtworkValidationError(
            code="ARTWORK_ASPECT_RATIO_INVALID",
            message=f"This {type_label} is {actual_width} × {actual_height} (approximately {actual_ratio:.2f}). {type_label} images need a {aspect_ratio_str} aspect ratio (approximately {expected_ratio:.2f}). Please choose or crop a suitable image.",
            details={
                "actual_ratio": round(actual_ratio, 3),
                "expected_ratio": round(expected_ratio, 3),
                "expected_aspect_ratio": aspect_ratio_str,
            },
        )

    import hashlib
    sha256 = hashlib.sha256(file_data).hexdigest()

    return {
        "width": actual_width,
        "height": actual_height,
        "format": actual_format,
        "mime_type": actual_mime,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "extension": MIME_TO_EXTENSION.get(actual_mime, ".bin"),
    }
