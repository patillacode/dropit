from app.settings import get_settings
from tests.conftest import USER_TOKEN


def test_upload_returns_url(client, tmp_path):
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
