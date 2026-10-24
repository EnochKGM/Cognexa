"""Generate + retrieval endpoints."""

from __future__ import annotations

import re

from fastapi import APIRouter

from ..errors import ApiError, FileNotFoundError_
from ..schemas import GenerateRequest, StudyMaterial
from ..services import get_generator
from ..storage import state

router = APIRouter(tags=["generation"])

UPLOAD_ID_FORMAT = 32  # uuid4().hex length


@router.post(
    "/api/generate",
    response_model=StudyMaterial,
    summary="Generate study material from an uploaded image",
)
async def generate(payload: GenerateRequest) -> StudyMaterial:
    """Produce structured study material for a stored upload.

    The active generator is chosen by `AI_PROVIDER`: `gemma4` calls Google AI
    Studio with the model `gemma-4-31b-it` and returns `is_demo: false` /
    `generator: "gemma4"`; `mock` returns clearly-labelled demo data. Provider
    failures surface as structured errors — there is no silent fallback.
    """
    upload_id = payload.upload_id.strip()

    if len(upload_id) != UPLOAD_ID_FORMAT or not re.match(r"^[0-9a-f]+$", upload_id):
        raise ApiError(
            422,
            "invalid_upload_id",
            "upload_id must be the server-generated id returned by POST /api/upload.",
        )

    record = state.get_upload(upload_id)
    if record is None:
        raise FileNotFoundError_(
            "Unknown upload_id. Upload an image with POST /api/upload first.",
            detail={"upload_id": upload_id},
        )

    generator = get_generator()
    result = await generator.generate(record.to_source_image())
    state.save_result(result)
    return result


@router.get(
    "/api/results/{result_id}",
    response_model=StudyMaterial,
    summary="Retrieve a generated result",
)
async def get_result(result_id: str) -> StudyMaterial:
    """Fetch a previously generated demo result by its server-generated id."""
    result = state.get_result(result_id)
    if result is None:
        raise FileNotFoundError_(
            "No result with that id. It may belong to a server restart — "
            "generate again from the workspace."
        )
    return result
