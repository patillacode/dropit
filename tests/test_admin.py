from sqlmodel import Session

from app.models import Page


def _add_page(engine, tmp_path, page_id="abc123", expires_at=None):
    (tmp_path / "pages" / page_id).write_bytes(b"<h1>Test</h1>")
    with Session(engine) as session:
        session.add(Page(id=page_id, expires_at=expires_at, token_hint="alice"))
        session.commit()


def test_admin_list_requires_token(client):
    res = client.get("/admin/pages", headers={"Authorization": "Bearer tok_test123"})
    assert res.status_code == 403


def test_admin_list_empty(client):
    res = client.get("/admin/pages", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 200
    assert res.json() == []


def test_admin_list_shows_pages(client, tmp_path):
    from app.settings import get_settings

    get_settings.cache_clear()

    res_upload = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("page.html", b"<h1>Hi</h1>", "text/html")},
    )
    assert res_upload.status_code == 200

    res = client.get("/admin/pages", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 200
    pages = res.json()
    assert len(pages) == 1
    assert "url" in pages[0]
    assert pages[0]["token_hint"] == "alice"
    assert "file_size" in pages[0]


def test_admin_delete_page(client, tmp_path):
    res_upload = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("page.html", b"<h1>Hi</h1>", "text/html")},
    )
    assert res_upload.status_code == 200
    page_id = res_upload.json()["url"].split("/p/")[1]

    res_del = client.delete(
        f"/admin/pages/{page_id}",
        headers={"Authorization": "Bearer admin_tok_xyz"},
    )
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] == page_id

    res_list = client.get("/admin/pages", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res_list.json() == []


def test_admin_delete_nonexistent_returns_404(client):
    res = client.delete(
        "/admin/pages/xxxxxx",
        headers={"Authorization": "Bearer admin_tok_xyz"},
    )
    assert res.status_code == 404


def test_admin_permanent_page_shows_null_expires(client, monkeypatch):
    from app.settings import get_settings

    monkeypatch.setenv("ALLOWED_TTLS", "1h,forever")
    get_settings.cache_clear()

    res = client.post(
        "/upload?ttl=forever",
        headers={"Authorization": "Bearer admin_tok_xyz"},
        files={"file": ("page.html", b"<h1>Hi</h1>", "text/html")},
    )
    assert res.status_code == 200

    res_list = client.get("/admin/pages", headers={"Authorization": "Bearer admin_tok_xyz"})
    pages = res_list.json()
    assert pages[0]["expires_at"] is None
