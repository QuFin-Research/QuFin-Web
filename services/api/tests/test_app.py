import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_security_headers(client):
    res = client.get("/v1/assets")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"


def test_cors_allows_configured_origin_only(client):
    preflight = {"Access-Control-Request-Method": "POST"}
    allowed = client.options(
        "/v1/decisions", headers={"Origin": "http://localhost:3000", **preflight}
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"

    blocked = client.options(
        "/v1/decisions", headers={"Origin": "https://evil.example", **preflight}
    )
    assert "access-control-allow-origin" not in blocked.headers
    simple = client.get("/v1/assets", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in simple.headers


def test_settings_from_environment(monkeypatch):
    monkeypatch.setenv("QUFIN_CORS_ORIGINS", "https://app.qufin.ai, http://localhost:3000")
    monkeypatch.setenv("QUFIN_ENVIRONMENT", "production")
    monkeypatch.setenv("QUFIN_COOKIE_SECURE", "true")
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["https://app.qufin.ai", "http://localhost:3000"]
    assert not settings.docs_enabled


def test_wildcard_cors_is_rejected(monkeypatch):
    monkeypatch.setenv("QUFIN_CORS_ORIGINS", "*")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_docs_hidden_in_production():
    client = TestClient(
        create_app(
            Settings(
                _env_file=None, environment="production", cookie_secure=True, auto_migrate=False
            )
        )
    )
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
