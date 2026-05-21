from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import create_app
from app.models import Page
from app.settings import get_settings


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_TOKENS", "alice:tok_test123")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BASE_URL", "http://testserver")
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
        yield c, engine, tmp_path


def test_serve_html(client_with_db):
    client, engine, tmp_path = client_with_db
    html = b"<h1>Hello world</h1>"
    page_id = "abc123"
    (tmp_path / "pages" / page_id).write_bytes(html)
    with Session(engine) as session:
        session.add(
            Page(
                id=page_id,
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                token_hint="alice",
            )
        )
        session.commit()
    response = client.get(f"/p/{page_id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.content == html


def test_missing_id_returns_404(client_with_db):
    client, _, _ = client_with_db
    response = client.get("/p/xxxxxx")
    assert response.status_code == 404


def test_expired_page_returns_404(client_with_db):
    client, engine, tmp_path = client_with_db
    page_id = "exp123"
    (tmp_path / "pages" / page_id).write_bytes(b"<h1>Old</h1>")
    with Session(engine) as session:
        session.add(
            Page(
                id=page_id,
                expires_at=datetime.now(UTC) - timedelta(hours=1),
                token_hint="alice",
            )
        )
        session.commit()
    response = client.get(f"/p/{page_id}")
    assert response.status_code == 404


def test_serve_returns_raw_html_not_download(client_with_db):
    client, engine, tmp_path = client_with_db
    page_id = "dl1234"
    (tmp_path / "pages" / page_id).write_bytes(b"<h1>Download test</h1>")
    with Session(engine) as session:
        session.add(
            Page(
                id=page_id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                token_hint="alice",
            )
        )
        session.commit()
    response = client.get(f"/p/{page_id}")
    assert "content-disposition" not in response.headers
