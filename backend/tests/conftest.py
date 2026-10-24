"""Shared pytest fixtures for the Cognexa backend tests."""

from __future__ import annotations

import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.main import create_app
from app.storage import state


def make_image_bytes(fmt: str = "PNG", size=(64, 48), color=(120, 80, 200)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A fresh app instance with an isolated upload directory per test."""
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MOCK_PROCESSING_DELAY", "0")
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    state.uploads.clear()
    state.results.clear()
    get_settings.cache_clear()


@pytest.fixture()
def png_bytes() -> bytes:
    return make_image_bytes("PNG")


@pytest.fixture()
def jpeg_bytes() -> bytes:
    return make_image_bytes("JPEG")


@pytest.fixture()
def uploaded_png(client, png_bytes):
    """A successfully uploaded PNG; returns (upload_id, response_json)."""
    response = client.post(
        "/api/upload",
        files={"file": ("textbook-page.png", png_bytes, "image/png")},
    )
    assert response.status_code == 200, response.text
    return response.json()
