"""Image upload validation.

Validation is deliberately layered so a malicious or accidental file cannot
reach storage:

1. filename extension          -> cheap early rejection
2. declared MIME type          -> must be image/png or image/jpeg
3. byte size                   -> hard limit (default 10 MB)
4. actual decoded content      -> Pillow decodes + fully loads the image and
                                  the *real* format must be PNG or JPEG

Uploaded files are stored under a private directory with a server-generated
filename (uuid); the user-provided filename is never trusted for storage.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from .errors import ApiError

SAFE_EXTENSIONS = {"png": ".png", "jpg": ".jpg", "jpeg": ".jpeg"}
MIME_TO_FORMATS = {
    "image/png": {"PNG"},
    "image/jpeg": {"JPEG"},
    "image/jpg": {"JPEG"},  # non-standard but common; content check still applies
}
FORMAT_TO_EXTENSION = {"PNG": ".png", "JPEG": ".jpg"}
CHUNK_SIZE = 64 * 1024


@dataclass
class ValidatedImage:
    upload_id: str
    stored_filename: str
    stored_path_name: str  # relative name inside the upload dir
    original_filename: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    stored_format: str


def _clean_original_name(filename: Optional[str]) -> str:
    """Keep only a safe basename for display purposes."""
    if not filename:
        return "textbook-page"
    name = filename.replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if ch.isprintable() and ch not in "/\\").strip()
    return name[:150] or "textbook-page"


def _extension_of(filename: str) -> str:
    if "." in filename:
        return filename.rsplit(".", 1)[1].lower()
    return ""


async def read_and_validate_image(upload: UploadFile, max_bytes: int) -> tuple[bytes, ValidatedImage]:
    """Read the upload fully into memory, validating every layer.

    Returns the image bytes plus metadata. Raises `ApiError` with a structured
    code for any validation failure.
    """
    original = _clean_original_name(upload.filename)

    # 1. Extension
    ext = _extension_of(original)
    if ext not in SAFE_EXTENSIONS:
        raise ApiError(
            415,
            "unsupported_file_type",
            f"Unsupported file extension '.{ext or '?'}'. Please upload a PNG, JPG or JPEG image.",
        )

    # 2. Declared MIME type
    content_type = (upload.content_type or "").lower()
    if content_type not in MIME_TO_FORMATS:
        raise ApiError(
            415,
            "unsupported_content_type",
            f"Unsupported content type '{content_type or 'unknown'}'. Only PNG and JPEG images are accepted.",
        )

    # 3. Size limit — stream in chunks, abort as soon as the limit is exceeded.
    declared_length: Optional[int] = None
    if upload.size is not None:
        declared_length = int(upload.size)
        if declared_length > max_bytes:
            raise _too_large(max_bytes)

    size_bytes = 0
    chunks: list[bytes] = []
    while True:
        chunk = await upload.read(CHUNK_SIZE)
        if not chunk:
            break
        size_bytes += len(chunk)
        if size_bytes > max_bytes:
            raise _too_large(max_bytes)
        chunks.append(chunk)
    data = b"".join(chunks)

    if size_bytes == 0:
        raise ApiError(400, "empty_file", "The uploaded file is empty.")
    if declared_length is not None and declared_length != size_bytes:
        # Trust the bytes we actually read, not the declared content length.
        size_bytes = declared_length if declared_length == len(data) else size_bytes

    # 4. Actual content — decode with Pillow and fully load the pixel data.
    try:
        probe = Image.open(__import__("io").BytesIO(data))
        detected_format = probe.format  # e.g. 'PNG' / 'JPEG'
        probe.verify()  # verifies file integrity for the detected format
        decoded = Image.open(__import__("io").BytesIO(data))
        decoded.load()  # force full decode to catch truncated payloads
        width, height = decoded.size
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ApiError(
            415,
            "invalid_image_content",
            "The file is not a valid PNG or JPEG image. It may be corrupted or disguised.",
        )

    if detected_format not in MIME_TO_FORMATS[content_type if content_type != "image/jpg" else "image/jpeg"]:
        raise ApiError(
            415,
            "content_type_mismatch",
            f"The file claims to be '{content_type}' but its actual content is '{detected_format}'.",
        )

    upload_id = uuid.uuid4().hex
    extension = FORMAT_TO_EXTENSION[detected_format]
    stored_name = f"{upload_id}{extension}"

    return data, ValidatedImage(
        upload_id=upload_id,
        stored_filename=stored_name,
        stored_path_name=stored_name,
        original_filename=original,
        content_type="image/jpeg" if detected_format == "JPEG" else "image/png",
        size_bytes=len(data),
        width=width,
        height=height,
        stored_format=detected_format,
    )


def _too_large(max_bytes: int) -> ApiError:
    return ApiError(
        413,
        "file_too_large",
        f"The file exceeds the {max_bytes // (1024 * 1024)} MB upload limit. "
        "Please upload a smaller image or a photo of a single page.",
    )
