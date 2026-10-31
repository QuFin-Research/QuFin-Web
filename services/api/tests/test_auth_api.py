import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from tests.conftest import PASSWORD, sign_up

COOKIE = "qufin_session"


def test_sign_up_signs_in_with_a_secure_cookie(client):
    res = client.post(
        "/v1/auth/sign-up", json={"email": "  Trader@Example.com ", "password": PASSWORD}
    )
    assert res.status_code == 201
    user = res.json()
    assert user["email"] == "trader@example.com"
    assert set(user) == {"id", "email", "createdAt"}

    cookie = res.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=604800" in cookie

    assert client.get("/v1/auth/me").json() == user


def test_password_hash_and_token_are_never_returned(client):
    body = client.post(
        "/v1/auth/sign-up", json={"email": "a@example.com", "password": PASSWORD}
    ).text
    assert "argon2" not in body
    assert PASSWORD not in body


def test_sign_up_validation(client):
    cases = [
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "a@example.com", "password": "short"},
        {"email": "a@example.com", "password": " " * 12},
        {"email": "a@example.com", "password": "x" * 129},
        {"email": "a@example.com", "password": PASSWORD, "isAdmin": True},
        {"email": "a@example.com"},
    ]
    for body in cases:
        assert client.post("/v1/auth/sign-up", json=body).status_code == 422, body


def test_duplicate_email_is_rejected(client):
    sign_up(client)
    res = client.post(
        "/v1/auth/sign-up", json={"email": "TRADER@example.com", "password": PASSWORD}
    )
    assert res.status_code == 409


def test_sign_in_and_out(client):
    sign_up(client)
    first_token = client.cookies.get(COOKIE)
    client.post("/v1/auth/sign-out")
    assert client.get("/v1/auth/me").status_code == 401

    res = client.post(
        "/v1/auth/sign-in", json={"email": "trader@example.com", "password": PASSWORD}
    )
    assert res.status_code == 200
    assert res.json()["email"] == "trader@example.com"
    assert client.cookies.get(COOKIE) != first_token
    assert client.get("/v1/auth/me").status_code == 200


def test_signed_out_token_cannot_be_reused(client):
    sign_up(client)
    token = client.cookies.get(COOKIE)
    assert client.post("/v1/auth/sign-out").status_code == 204
    client.cookies.set(COOKIE, token)
    assert client.get("/v1/auth/me").status_code == 401


def test_wrong_password_and_unknown_email_look_the_same(client):
    sign_up(client)
    client.post("/v1/auth/sign-out")
    wrong = client.post(
        "/v1/auth/sign-in", json={"email": "trader@example.com", "password": "wrong password!"}
    )
    unknown = client.post(
        "/v1/auth/sign-in", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Incorrect email or password"}


def test_forged_or_missing_session_is_rejected(client):
    assert client.get("/v1/auth/me").status_code == 401
    client.cookies.set(COOKIE, "forged-token")
    assert client.get("/v1/auth/me").status_code == 401


def test_expired_session_is_rejected(app, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.stores import users

    with TestClient(app) as client:
        sign_up(client)
        later = datetime.now(UTC) + timedelta(hours=169)

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return later

        monkeypatch.setattr(users, "datetime", Clock)
        assert client.get("/v1/auth/me").status_code == 401


def test_sign_in_is_rate_limited(app):
    app.state.auth_limiter.limit = 3
    with TestClient(app) as client:
        body = {"email": "trader@example.com", "password": "wrong password!"}
        statuses = [client.post("/v1/auth/sign-in", json=body).status_code for _ in range(4)]
        assert statuses == [401, 401, 401, 429]
        res = client.post("/v1/auth/sign-in", json=body)
        assert int(res.headers["retry-after"]) > 0


def test_cross_site_writes_are_refused(user_client):
    res = user_client.post("/v1/auth/sign-out", headers={"Origin": "https://evil.example"})
    assert res.status_code == 403
    assert user_client.get("/v1/auth/me").status_code == 200

    allowed = user_client.post("/v1/auth/sign-out", headers={"Origin": "http://localhost:3000"})
    assert allowed.status_code == 204


def test_credentialed_cors_for_configured_origin(client):
    res = client.get("/v1/auth/me", headers={"Origin": "http://localhost:3000"})
    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert res.headers["access-control-allow-credentials"] == "true"


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/v1/decisions", None),
        ("post", "/v1/decisions", {}),
        ("delete", "/v1/decisions/00000000-0000-0000-0000-000000000000", None),
        ("post", "/v1/backtests", {}),
    ],
)
def test_protected_endpoints_require_sign_in(client, method, path, body):
    kwargs = {"json": body} if body is not None else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


def test_market_data_stays_public(client):
    assert client.get("/v1/assets").status_code == 200


def test_production_requires_secure_cookies():
    with pytest.raises(ValueError, match="COOKIE_SECURE"):
        Settings(_env_file=None, environment="production")
    Settings(_env_file=None, environment="production", cookie_secure=True)
