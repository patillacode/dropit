import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import create_app
from app.settings import get_settings


@pytest.fixture(name="db_session")
def db_session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("UPLOAD_TOKENS", "alice:tok_test123")
    monkeypatch.setenv("BASE_URL", "http://localhost:52031")
    monkeypatch.setenv("DATA_DIR", "/tmp/dropit-test")
    os.makedirs("/tmp/dropit-test/pages", exist_ok=True)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_TOKENS", "alice:tok_test123")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BASE_URL", "http://testserver")
    monkeypatch.setenv("ADMIN_TOKEN", "admin_tok_xyz")
    get_settings.cache_clear()
    (tmp_path / "pages").mkdir()

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as c:
        yield c
