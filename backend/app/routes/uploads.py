"""Upload endpoints: validate + store textbook images, stream them back for review."""

from __future__ import annotations

import re

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response

from ..config import get_settings
from ..errors import ApiError, FileNotFoundError_
from ..schemas import UploadResponse
from ..storage import UploadRecord, ensure_upload_dir, state
from ..validation import read_and_validate_image

router = APIRouter(tags=["uploads"])

UPLOAD_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@router.post("/api/upload", response_model=UploadResponse, summary="Upload a textbook image")
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    """Validate an uploaded PNG/JPEG and store it privately.

    Enforces: allowed extension + MIME type, 10 MB size limit and a genuine
    decodable PNG/JPEG payload.  The stored filename is a server-generated
    UUID — the user-provided filename is never used for storage.
    """
    settings = get_settings()

    data, meta = await read_and_validate_image(file, settings.max_upload_bytes)

    upload_dir = ensure_upload_dir(settings.upload_path)
    stored_path = upload_dir / meta.stored_path_name
    stored_path.write_bytes(data)

    state.save_upload(
        UploadRecord(
            upload_id=meta.upload_id,
            stored_path=stored_path,
            original_filename=meta.original_filename,
            content_type=meta.content_type,
            size_bytes=meta.size_bytes,
            width=meta.width,
            height=meta.height,
            stored_format=meta.stored_format,
        )
    )

    return UploadResponse(
        upload_id=meta.upload_id,
        filename=meta.original_filename,
        content_type=meta.content_type,
        size_bytes=meta.size_bytes,
        width=meta.width,
        height=meta.height,
        stored_format=meta.stored_format,
    )


@router.get("/api/uploads/{upload_id}", summary="Review an uploaded image")
async def get_upload_image(upload_id: str) -> Response:
    """Stream a stored upload back for the Source Image review tab.

    Files live in a private directory and are reachable only via this endpoint
    with an unguessable server-generated id; path traversal is impossible
    because ids are validated against a strict hex pattern.
    """
    if not UPLOAD_ID_PATTERN.match(upload_id):
        raise FileNotFoundError_("Upload not found.")

    record = state.get_upload(upload_id)
    if record is None or not record.stored_path.exists():
        raise FileNotFoundError_("Upload not found or expired.")

    data = record.stored_path.read_bytes()
    return Response(
        content=data,
        media_type=record.content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": f'inline; filename="{record.original_filename}"',
        },
    )
