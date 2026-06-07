from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.database as db_mod
from app.database import get_session
from app.main import create_app
from app.models import Page
from app.banner import inject_banner
from app.settings import get_settings

CONTENT_DOMAIN = "testcontent.test"
USER_TOKEN = "tok_test123"


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_TOKENS", "alice:tok_test123")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CONTENT_DOMAIN", CONTENT_DOMAIN)
    get_settings.cache_clear()
    (tmp_path / "pages").mkdir()

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    db_mod._engine = engine  # lifespan reuses this; no file-backed engine created

    def override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as c:
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
    assert b"<h1>Hello world</h1>" in response.content


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


def test_mixed_case_id_served_via_lowercase_subdomain(client_with_db):
    """Regression: pages with mixed-case IDs (from old token_urlsafe generator) must be
    accessible via their lowercase subdomain, since HTTP hostnames are case-insensitive."""
    client, engine, tmp_path = client_with_db
    stored_id = "aBcD1234"
    html = b"<h1>Mixed case</h1>"
    (tmp_path / "pages" / stored_id).write_bytes(html)
    with Session(engine) as session:
        session.add(
            Page(
                id=stored_id,
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                token_hint="alice",
            )
        )
        session.commit()
    response = client.get("/", headers={"host": _content_host(stored_id.lower())})
    assert response.status_code == 200
    assert b"<h1>Mixed case</h1>" in response.content


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


def test_page_not_found_via_subdomain(client):
    res = client.get("/", headers={"Host": "doesnotexist.testcontent.test"})
    assert res.status_code == 404


def test_page_file_missing_from_disk(client, tmp_path):
    content = b"<html><body>hello</body></html>"
    upload_res = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("test.html", content, "text/html")},
    )
    assert upload_res.status_code == 200
    page_id = upload_res.json()["url"].split("//")[1].split(".")[0]

    (tmp_path / "pages" / page_id).unlink()

    res = client.get("/", headers={"Host": f"{page_id}.testcontent.test"})
    assert res.status_code == 404


def test_reserved_subdomain_passes_through(client):
    res = client.get("/", headers={"Host": "www.testcontent.test"})
    assert res.status_code == 200


def test_inject_banner_after_body_tag():
    html = b"<html><body><h1>Hello</h1></body></html>"
    result = inject_banner(html, base_url="https://dropit.example.com")
    assert b'id="dropit-banner"' in result
    assert b'id="dropit-spacer"' in result
    banner_pos = result.index(b'id="dropit-banner"')
    content_pos = result.index(b"<h1>Hello</h1>")
    assert banner_pos < content_pos


def test_inject_banner_no_body_tag():
    html = b"<h1>Fragment</h1>"
    result = inject_banner(html, base_url="https://dropit.example.com")
    assert b'id="dropit-banner"' in result
    assert b'id="dropit-spacer"' in result
    assert b"<h1>Fragment</h1>" in result


def test_inject_banner_contains_base_url():
    html = b"<body><p>hi</p></body>"
    result = inject_banner(html, base_url="https://dropit.patilla.es")
    assert b"https://dropit.patilla.es" in result


def test_inject_banner_spacer_height_matches_banner():
    html = b"<body><p>hi</p></body>"
    result = inject_banner(html, base_url="https://dropit.example.com").decode()
    assert 'id="dropit-banner"' in result
    assert 'id="dropit-spacer"' in result


def test_serve_page_includes_banner_when_enabled(client_with_db, monkeypatch):
    monkeypatch.setenv("BANNER_ENABLED", "true")
    get_settings.cache_clear()
    client, engine, tmp_path = client_with_db
    page_id = "bnr001"
    (tmp_path / "pages" / page_id).write_bytes(b"<body><h1>Hi</h1></body>")
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
    assert 'id="dropit-banner"' in response.text
    assert 'id="dropit-spacer"' in response.text


def test_serve_page_no_banner_when_disabled(client_with_db, monkeypatch):
    monkeypatch.setenv("BANNER_ENABLED", "false")
    get_settings.cache_clear()
    client, engine, tmp_path = client_with_db
    page_id = "bnr002"
    (tmp_path / "pages" / page_id).write_bytes(b"<body><h1>Hi</h1></body>")
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
    assert 'id="dropit-banner"' not in response.text
