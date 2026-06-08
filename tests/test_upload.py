import secrets
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select
from structlog.testing import capture_logs

from app.models import Collection, Page
from app.settings import get_settings
from tests.conftest import ADMIN_TOKEN, USER_TOKEN


def test_upload_returns_url(client):
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "expires_at" in data
    assert data["url"].startswith("https://") and data["url"].endswith(".testcontent.test")


def test_upload_rejects_invalid_token(client):
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer wrong"},
        files={"file": ("test.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert response.status_code == 401


def test_upload_rejects_invalid_ttl(client):
    response = client.post(
        "/upload?ttl=5m",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
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
    html = b"<!doctype html><html><body>hi</body></html>"
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", html, "text/html")},
    )
    assert response.status_code == 200
    page_id = response.json()["url"].split("//")[1].split(".")[0]
    assert (tmp_path / "pages" / page_id).read_bytes() == html


def test_upload_forever_ttl_rejected_for_user(client, monkeypatch):
    monkeypatch.setenv("ALLOWED_TTLS", "1h,6h,24h,forever")
    get_settings.cache_clear()
    response = client.post(
        "/upload?ttl=forever",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert response.status_code == 403


def test_upload_forever_ttl_allowed_for_admin(client, monkeypatch):
    monkeypatch.setenv("ALLOWED_TTLS", "1h,6h,24h,forever")
    get_settings.cache_clear()
    response = client.post(
        "/upload?ttl=forever",
        headers={"Authorization": "Bearer admin_tok_xyz"},
        files={"file": ("test.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert response.status_code == 200
    assert response.json()["expires_at"] is None


def test_upload_ttl_exceeds_max_user_ttl(client, monkeypatch):
    monkeypatch.setenv("ALLOWED_TTLS", "1h,6h,24h,48h,7d")
    monkeypatch.setenv("MAX_USER_TTL", "24h")
    get_settings.cache_clear()
    response = client.post(
        "/upload?ttl=48h",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert response.status_code == 403


def test_upload_admin_bypasses_max_user_ttl(client, monkeypatch):
    monkeypatch.setenv("ALLOWED_TTLS", "1h,6h,24h,48h,7d")
    monkeypatch.setenv("MAX_USER_TTL", "24h")
    get_settings.cache_clear()
    response = client.post(
        "/upload?ttl=7d",
        headers={"Authorization": "Bearer admin_tok_xyz"},
        files={"file": ("test.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert response.status_code == 200


def test_upload_rejects_oversized_via_body_read(client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE", "30")
    get_settings.cache_clear()
    # 42-byte body — exceeds 30-byte limit
    oversized = b"<!doctype html><html><body>hi</body></html>"
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", oversized, "text/html")},
    )
    assert response.status_code == 413


def test_upload_rate_limited(client):
    content = b"<!doctype html><html><body>hi</body></html>"
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}
    for _ in range(5):
        r = client.post(
            "/upload",
            headers=headers,
            files={"file": ("test.html", content, "text/html")},
        )
        assert r.status_code == 200
    r = client.post(
        "/upload",
        headers=headers,
        files={"file": ("test.html", content, "text/html")},
    )
    assert r.status_code == 429
    assert r.json()["detail"] == "Too many requests — please slow down and try again shortly"


def test_upload_rejects_html_ext_with_non_html_content(client):
    # .html extension but content is not HTML — must be rejected
    response = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("malicious.html", b"definitely not html content here", "text/html")},
    )
    assert response.status_code == 422


def test_upload_rejects_non_utf8_content(client):
    # .html extension but bytes are not valid UTF-8
    bad_bytes = b"<!doctype html>\xe9\xe0"
    response = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("page.html", bad_bytes, "text/html")},
    )
    assert response.status_code == 422


def test_upload_expires_at_has_utc_suffix(client):
    content = b"<!doctype html><html><body>hi</body></html>"
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("test.html", content, "text/html")},
    )
    assert r.status_code == 200
    expires_at = r.json()["expires_at"]
    assert expires_at is not None
    assert expires_at.endswith("Z"), f"expected Z suffix, got: {expires_at!r}"


def test_upload_invalid_content_length_triggers_streaming_size_check(client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE", "10")
    get_settings.cache_clear()
    try:
        content = b"<html>" + b"x" * 20 + b"</html>"
        res = client.post(
            "/upload",
            headers={
                "Authorization": f"Bearer {USER_TOKEN}",
                "Content-Length": "notanumber",
            },
            files={"file": ("test.html", content, "text/html")},
        )
        assert res.status_code == 413
    finally:
        get_settings.cache_clear()


def test_upload_id_collision_exhausted(client, monkeypatch):
    fixed_id = "aaaabbbb"
    monkeypatch.setattr(secrets, "token_hex", lambda _: fixed_id)

    with Session(client.app.state.engine) as session:
        page = Page(
            id=fixed_id,
            token_hint="hint",
            expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        )
        session.add(page)
        session.commit()

    content = b"<html><body>test</body></html>"
    with TestClient(client.app, raise_server_exceptions=False) as no_raise_client:
        res = no_raise_client.post(
            "/upload",
            headers={"Authorization": f"Bearer {USER_TOKEN}"},
            files={"file": ("test.html", content, "text/html")},
        )
    assert res.status_code == 500


def test_upload_success_is_logged(client):
    content = b"<!doctype html><html><body>hello</body></html>"
    with capture_logs() as cap:
        res = client.post(
            "/upload",
            files={"file": ("test.html", content, "text/html")},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert res.status_code == 200
    successes = [entry for entry in cap if entry.get("event") == "upload.success"]
    assert len(successes) == 1
    log = successes[0]
    assert log["size"] == len(content)
    assert log["ttl"] == "24h"
    assert "page_id" in log
    assert log["user"] == "admin"


def test_upload_too_large_is_logged(client):
    big_content = b"<!doctype html>" + b"x" * 6_000_000
    with capture_logs() as cap:
        res = client.post(
            "/upload",
            files={"file": ("big.html", big_content, "text/html")},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert res.status_code == 413
    failures = [entry for entry in cap if entry.get("event") == "upload.failure"]
    assert len(failures) == 1
    assert failures[0]["reason"] == "too_large"


def test_upload_invalid_content_is_logged(client):
    with capture_logs() as cap:
        res = client.post(
            "/upload",
            files={"file": ("test.html", b"not html at all", "text/html")},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert res.status_code == 422
    failures = [entry for entry in cap if entry.get("event") == "upload.failure"]
    assert len(failures) == 1
    assert failures[0]["reason"] == "invalid_content"


def test_upload_with_collection(client):
    content = b"<!doctype html><html><body>hi</body></html>"
    response = client.post(
        "/upload?collection=work",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("test.html", content, "text/html")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["collection"] == "work"
    assert "url" in data
    assert "expires_at" in data

    with Session(client.app.state.engine) as session:
        colls = session.exec(select(Collection).where(Collection.name == "work")).all()
        assert len(colls) == 1
        assert colls[0].name == "work"


def test_upload_with_existing_collection(client):
    content = b"<!doctype html><html><body>hi</body></html>"
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}

    r1 = client.post(
        "/upload?collection=archive",
        headers=headers,
        files={"file": ("test1.html", content, "text/html")},
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/upload?collection=archive",
        headers=headers,
        files={"file": ("test2.html", content, "text/html")},
    )
    assert r2.status_code == 200

    with Session(client.app.state.engine) as session:
        colls = session.exec(select(Collection).where(Collection.name == "archive")).all()
        assert len(colls) == 1


def test_upload_normalizes_collection_name(client):
    content = b"<!doctype html><html><body>hi</body></html>"
    response = client.post(
        "/upload?collection=MyCollection",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("test.html", content, "text/html")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["collection"] == "mycollection"


def test_upload_without_collection(client):
    content = b"<!doctype html><html><body>hi</body></html>"
    response = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("test.html", content, "text/html")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["collection"] is None


def test_upload_collection_requires_db_user(client):
    content = b"<!doctype html><html><body>hi</body></html>"
    response = client.post(
        "/upload?collection=foo",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        files={"file": ("test.html", content, "text/html")},
    )
    assert response.status_code == 422
    assert "Collections require a DB user token" in response.json()["detail"]


def test_upload_collection_empty_name_rejected(client):
    content = b"<!doctype html><html><body>hi</body></html>"
    response = client.post(
        "/upload?collection=   ",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("test.html", content, "text/html")},
    )
    assert response.status_code == 422
    assert "Collection name cannot be empty" in response.json()["detail"]
