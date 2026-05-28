from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import create_app
from app.models import Page
from app.settings import get_settings

CONTENT_DOMAIN = "testcontent.test"


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_TOKENS", "alice:tok_test123")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BASE_URL", "http://testserver")
    monkeypatch.setenv("CONTENT_DOMAIN", CONTENT_DOMAIN)
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
        c.app.state.engine = engine
        yield c, engine, tmp_path


def _content_host(page_id: str) -> str:
    return f"{page_id}.{CONTENT_DOMAIN}"


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
    response = client.get("/", headers={"host": _content_host(page_id)})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.content == html


def test_missing_id_returns_404_html(client_with_db):
    client, _, _ = client_with_db
    response = client.get("/p/xxxxxx")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "This page doesn" in response.text and "t exist" in response.text


def test_expired_page_returns_404_html(client_with_db):
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
    response = client.get("/", headers={"host": _content_host(page_id)})
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "This page has expired" in response.text


def test_unknown_route_returns_404_html(client_with_db):
    client, _, _ = client_with_db
    response = client.get("/nonexistent-route")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")


def test_expired_naive_utc_returns_404(client_with_db):
    """Regression: naive UTC expires_at must be caught by the serve check (timezone bug fix)."""
    client, engine, tmp_path = client_with_db
    page_id = "naivexp"
    (tmp_path / "pages" / page_id).write_bytes(b"<h1>Old</h1>")
    with Session(engine) as session:
        session.add(
            Page(
                id=page_id,
                expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
                token_hint="alice",
            )
        )
        session.commit()
    response = client.get("/", headers={"host": _content_host(page_id)})
    assert response.status_code == 404
    assert "expired" in response.text


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
    response = client.get("/", headers={"host": _content_host(page_id)})
    assert response.status_code == 200
    assert "content-disposition" not in response.headers
