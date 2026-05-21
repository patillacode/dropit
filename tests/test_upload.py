import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import create_app
from app.settings import get_settings


@pytest.fixture
def client(tmp_path, monkeypatch):
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
        yield c


def test_upload_returns_url(client, tmp_path):
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", b"<h1>Hello</h1>", "text/html")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "expires_at" in data
    assert data["url"].startswith("http://testserver/p/")


def test_upload_rejects_invalid_token(client):
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer wrong"},
        files={"file": ("test.html", b"<h1>Hi</h1>", "text/html")},
    )
    assert response.status_code == 401


def test_upload_rejects_invalid_ttl(client):
    response = client.post(
        "/upload?ttl=5m",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", b"<h1>Hi</h1>", "text/html")},
    )
    assert response.status_code == 422


def test_upload_rejects_non_html(client):
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.txt", b"just text", "text/plain")},
    )
    assert response.status_code == 422


def test_upload_rejects_oversized_file(client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE", "10")
    get_settings.cache_clear()
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", b"<h1>Too big</h1>", "text/html")},
    )
    assert response.status_code == 413


def test_upload_stores_file(client, tmp_path):
    html = b"<h1>Stored</h1>"
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", html, "text/html")},
    )
    assert response.status_code == 200
    page_id = response.json()["url"].split("/p/")[1]
    assert (tmp_path / "pages" / page_id).read_bytes() == html
