"""Upload validation tests: extension, MIME, size and real image content."""

import io

from PIL import Image

from .conftest import make_image_bytes


def test_upload_valid_png(client, png_bytes):
    response = client.post(
        "/api/upload",
        files={"file": ("page.png", png_bytes, "image/png")},
    )
    assert response.status_code == 200
    body = response.json()

    # Server-generated id (uuid4 hex), never derived from the filename.
    assert len(body["upload_id"]) == 32
    assert body["upload_id"].isalnum()
    assert not body["upload_id"].startswith("page")

    assert body["filename"] == "page.png"
    assert body["content_type"] == "image/png"
    assert body["stored_format"] == "PNG"
    assert body["size_bytes"] == len(png_bytes)
    assert body["width"] == 64
    assert body["height"] == 48


def test_upload_valid_jpeg(client, jpeg_bytes):
    response = client.post(
        "/api/upload",
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stored_format"] == "JPEG"
    assert body["content_type"] == "image/jpeg"
    assert body["width"] == 64


def test_upload_rejects_unsupported_extension(client, png_bytes):
    response = client.post(
        "/api/upload",
        files={"file": ("notes.txt", png_bytes, "image/png")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_upload_rejects_unsupported_mime_type(client, png_bytes):
    response = client.post(
        "/api/upload",
        files={"file": ("page.png", png_bytes, "application/pdf")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_content_type"


def test_upload_rejects_fake_image_content(client):
    """A text file renamed to .png with a PNG MIME type must be rejected."""
    response = client.post(
        "/api/upload",
        files={"file": ("fake.png", b"definitely not an image", "image/png")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "invalid_image_content"


def test_upload_rejects_content_type_mismatch(client, jpeg_bytes):
    """JPEG bytes labelled as image/png must be rejected by content inspection."""
    response = client.post(
        "/api/upload",
        files={"file": ("mislabeled.png", jpeg_bytes, "image/png")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "content_type_mismatch"


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/api/upload",
        files={"file": ("page.png", b"", "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_file"


def test_upload_rejects_oversized_file(client, monkeypatch):
    """Files above the limit are rejected before content is decoded."""
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")

    from app.config import get_settings

    get_settings.cache_clear()
    try:
        oversized = b"\x89PNG\r\n\x1a\n" + b"0" * (1_200_000)
        response = client.post(
            "/api/upload",
            files={"file": ("big.png", oversized, "image/png")},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "file_too_large"
    finally:
        get_settings.cache_clear()


def test_upload_truncated_image_is_rejected(client):
    """A truncated PNG (valid header, cut short) must not be stored."""
    full = make_image_bytes("PNG", size=(400, 400))
    truncated = full[: len(full) // 2]
    response = client.post(
        "/api/upload",
        files={"file": ("broken.png", truncated, "image/png")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "invalid_image_content"


def test_uploaded_file_is_stored_privately_and_served_by_id(client, uploaded_png):
    upload_id = uploaded_png["upload_id"]

    # The stored file is only reachable through the API id endpoint.
    response = client.get(f"/api/uploads/{upload_id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")

    # Invalid ids (e.g. traversal attempts) 404 safely.
    assert client.get("/api/uploads/../../etc/passwd").status_code in (404, 422, 400)
    assert client.get("/api/uploads/not-a-real-id").status_code == 404
