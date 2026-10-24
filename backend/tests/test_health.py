"""Health endpoint tests."""


def test_health_returns_ok_and_reports_ai_not_configured(client):
    response = client.get("/api/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "cognexa-backend"

    # This test suite runs with AI_PROVIDER=mock, so no AI integration is active.
    assert body["ai_configured"] is False
    assert body["ai_provider"] == "mock"
    assert body["demo_mode"] is True
    assert body["reserved_gemma_model"] == "gemma-4-31b-it"
    assert body["max_upload_mb"] == 10


def test_health_is_structured_json(client):
    body = client.get("/api/health").json()
    for key in ("status", "ai_provider", "ai_configured", "reserved_gemma_model"):
        assert key in body
