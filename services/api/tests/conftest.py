from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.stores.decisions import get_session, make_engine


@pytest.fixture
def client() -> Iterator[TestClient]:
    """App with a fresh in-memory decision database per test."""
    factory = sessionmaker(make_engine("sqlite://"), expire_on_commit=False)

    def session_override() -> Iterator[Session]:
        with factory() as session:
            yield session

    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as test_client:
        yield test_client
