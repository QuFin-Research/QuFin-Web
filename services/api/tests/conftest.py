from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.stores.db import create_all, get_session, make_engine

PASSWORD = "correct horse battery staple"


@pytest.fixture
def app():
    """App with a fresh in-memory database per test."""
    engine = make_engine("sqlite://")
    create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session_override() -> Iterator[Session]:
        with factory() as session:
            yield session

    application = create_app(Settings(_env_file=None, auto_migrate=False))
    application.dependency_overrides[get_session] = session_override
    return application


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    """Anonymous client."""
    with TestClient(app) as test_client:
        yield test_client


def sign_up(client: TestClient, email: str = "trader@example.com") -> dict:
    res = client.post("/v1/auth/sign-up", json={"email": email, "password": PASSWORD})
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture
def user_client(app) -> Iterator[TestClient]:
    """Client signed in as a fresh user (the session cookie is kept by the client)."""
    with TestClient(app) as test_client:
        sign_up(test_client)
        yield test_client
