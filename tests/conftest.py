import os

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


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
