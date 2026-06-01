import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.auth import hash_token
from app.database import get_session
from app.main import create_app
from app.models import User
from app.settings import get_settings

USER_TOKEN = "tok_test123"
ADMIN_TOKEN = "admin_tok_xyz"


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
    monkeypatch.setenv("BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("CONTENT_DOMAIN", "testcontent.test")
    monkeypatch.setenv("DATA_DIR", "/tmp/dropit-test")
    os.makedirs("/tmp/dropit-test/pages", exist_ok=True)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BASE_URL", "http://testserver")
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    get_settings.cache_clear()
    (tmp_path / "pages").mkdir()

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(name="alice", token_hash=hash_token(USER_TOKEN), is_admin=False))
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as c:
        c.app.state.engine = engine
        yield c
