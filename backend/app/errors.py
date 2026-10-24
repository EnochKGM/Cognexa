"""Structured error handling for the Cognexa backend.

Every error response has the same shape so the frontend can render useful,
honest messages:

    {"error": {"code": "file_too_large", "message": "...", "detail": null}}
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("mindmap_ai")


def error_body(code: str, message: str, detail: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "detail": detail}}


def error_response(status_code: int, code: str, message: str, detail: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_body(code, message, detail))


class ApiError(Exception):
    """Domain error carrying an HTTP status, machine code and human message."""

    def __init__(self, status_code: int, code: str, message: str, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail


class FileNotFoundError_(ApiError):
    def __init__(self, message: str = "The requested resource was not found.", detail: Any = None):
        super().__init__(404, "not_found", message, detail)


class ProviderNotAvailableError(ApiError):
    """Raised when the configured AI provider cannot serve requests.

    The Gemma 4 path raises this instead of silently falling back to mock data
    or switching to a different model.
    """

    def __init__(self, message: str, detail: Any = None):
        super().__init__(503, "ai_provider_unavailable", message, detail)


class AiGenerationError(ApiError):
    """Raised when an AI provider responds but its output is unusable.

    Used for malformed or incomplete model output; the backend never invents
    missing study material.
    """

    def __init__(self, message: str, detail: Any = None, code: str = "ai_generation_failed"):
        super().__init__(502, code, message, detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.detail)

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = "http_error"
        if exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 405:
            code = "method_not_allowed"
        detail: Optional[Any] = exc.detail if not isinstance(exc.detail, str) else None
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return error_response(exc.status_code, code, message, detail)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidation) -> JSONResponse:
        return error_response(
            422,
            "validation_error",
            "The request payload failed validation.",
            detail=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "internal_error", "An unexpected server error occurred.")


# Alias used above for readability in the handler signature.
RequestValidation = RequestValidationError
