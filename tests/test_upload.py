from app.settings import get_settings


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
    assert data["url"].startswith("https://") and data["url"].endswith(".testcontent.test")


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
    page_id = response.json()["url"].split("//")[1].split(".")[0]
    assert (tmp_path / "pages" / page_id).read_bytes() == html


def test_upload_forever_ttl_rejected_for_user(client, monkeypatch):
    monkeypatch.setenv("ALLOWED_TTLS", "1h,6h,24h,forever")
    get_settings.cache_clear()
    response = client.post(
        "/upload?ttl=forever",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", b"<h1>Hi</h1>", "text/html")},
    )
    assert response.status_code == 403


def test_upload_forever_ttl_allowed_for_admin(client, monkeypatch):
    monkeypatch.setenv("ALLOWED_TTLS", "1h,6h,24h,forever")
    get_settings.cache_clear()
    response = client.post(
        "/upload?ttl=forever",
        headers={"Authorization": "Bearer admin_tok_xyz"},
        files={"file": ("test.html", b"<h1>Hi</h1>", "text/html")},
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
        files={"file": ("test.html", b"<h1>Hi</h1>", "text/html")},
    )
    assert response.status_code == 403


def test_upload_admin_bypasses_max_user_ttl(client, monkeypatch):
    monkeypatch.setenv("ALLOWED_TTLS", "1h,6h,24h,48h,7d")
    monkeypatch.setenv("MAX_USER_TTL", "24h")
    get_settings.cache_clear()
    response = client.post(
        "/upload?ttl=7d",
        headers={"Authorization": "Bearer admin_tok_xyz"},
        files={"file": ("test.html", b"<h1>Hi</h1>", "text/html")},
    )
    assert response.status_code == 200


def test_upload_rejects_oversized_via_body_read(client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE", "20")
    get_settings.cache_clear()
    # 25-byte body — exceeds 20-byte limit
    oversized = b"<h1>Oversized file!!</h1>"
    response = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("test.html", oversized, "text/html")},
    )
    assert response.status_code == 413
