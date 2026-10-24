"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/api/health", response_model=HealthResponse, summary="Service health")
async def health() -> HealthResponse:
    """Liveness + configuration status.

    Reports which generator is active and whether GOOGLE_API_KEY is configured,
    without ever exposing the key itself.
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="cognexa-backend",
        demo_mode=settings.ai_provider == "mock",
        ai_provider=settings.ai_provider,
        ai_configured=settings.ai_configured,
        reserved_gemma_model=settings.gemma_model,
        max_upload_mb=settings.max_upload_mb,
    )
