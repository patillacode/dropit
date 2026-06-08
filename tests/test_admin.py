from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import Session
from structlog.testing import capture_logs

from app.auth import hash_token
from app.models import Collection, Page, User
from tests.conftest import ADMIN_TOKEN, USER_TOKEN


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
        files={"file": ("page.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
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
        files={"file": ("page.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert res_upload.status_code == 200
    page_id = res_upload.json()["url"].split("//")[1].split(".")[0]

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


def test_cleanup_status_no_runs(client):
    res = client.get("/admin/cleanup/status", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 200
    data = res.json()
    assert data["last_run"] is None
    assert data["next_run"] is not None


def test_cleanup_history_empty(client):
    res = client.get("/admin/cleanup/history", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 200
    assert res.json() == []


def test_cleanup_trigger_returns_count(client):
    from app.settings import get_settings

    settings = get_settings()
    pages_dir = Path(settings.data_dir) / "pages"
    page_id = "exp0001"
    (pages_dir / page_id).write_bytes(b"<h1>Old</h1>")
    engine = client.app.state.engine
    with Session(engine) as session:
        session.add(
            Page(
                id=page_id,
                expires_at=(datetime.now(UTC) - timedelta(seconds=1)).replace(tzinfo=None),
                token_hint="alice",
            )
        )
        session.commit()

    res = client.post("/admin/cleanup/trigger", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 200
    assert res.json()["deleted"] == 1

    res2 = client.get("/admin/cleanup/history", headers={"Authorization": "Bearer admin_tok_xyz"})
    runs = res2.json()
    assert len(runs) == 1
    assert runs[0]["triggered_by"] == "admin"
    assert runs[0]["deleted_count"] == 1


def test_cleanup_status_after_run(client):
    client.post("/admin/cleanup/trigger", headers={"Authorization": "Bearer admin_tok_xyz"})
    res = client.get("/admin/cleanup/status", headers={"Authorization": "Bearer admin_tok_xyz"})
    data = res.json()
    assert data["last_run"] is not None
    assert data["last_run"]["triggered_by"] == "admin"


def test_cleanup_requires_admin(client):
    res = client.get("/admin/cleanup/status", headers={"Authorization": "Bearer tok_test123"})
    assert res.status_code == 403


def test_admin_list_file_size_matches_upload(client):
    content = b"<!doctype html><html><body>size-test</body></html>"
    res = client.post(
        "/upload",
        headers={"Authorization": "Bearer tok_test123"},
        files={"file": ("page.html", content, "text/html")},
    )
    assert res.status_code == 200

    res_list = client.get("/admin/pages", headers={"Authorization": "Bearer admin_tok_xyz"})
    pages = res_list.json()
    assert len(pages) == 1
    assert pages[0]["file_size"] == len(content)


def test_admin_permanent_page_shows_null_expires(client, monkeypatch):
    from app.settings import get_settings

    monkeypatch.setenv("ALLOWED_TTLS", "1h,forever")
    get_settings.cache_clear()

    res = client.post(
        "/upload?ttl=forever",
        headers={"Authorization": "Bearer admin_tok_xyz"},
        files={"file": ("page.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert res.status_code == 200

    res_list = client.get("/admin/pages", headers={"Authorization": "Bearer admin_tok_xyz"})
    pages = res_list.json()
    assert pages[0]["expires_at"] is None


def test_trigger_cleanup_engine_unavailable(client):
    del client.app.state.engine
    res = client.post(
        "/admin/cleanup/trigger",
        headers={"Authorization": "Bearer admin_tok_xyz"},
    )
    assert res.status_code == 503
    assert res.json()["detail"] == "Engine not available"


def test_delete_page_logs_actor(client):
    res = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("page.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert res.status_code == 200
    page_id = res.json()["url"].split("//")[1].split(".")[0]

    with capture_logs() as cap:
        client.delete(
            f"/admin/pages/{page_id}",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    deletions = [entry for entry in cap if entry.get("event") == "page.deleted"]
    assert len(deletions) == 1
    assert deletions[0]["actor"] == "admin"


def test_delete_page_logs_db_actor(client):
    with Session(client.app.state.engine) as session:
        session.add(User(name="carol", token_hash=hash_token("tok_carol_admin"), is_admin=True))
        session.commit()

    res = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("page.html", b"<!doctype html><html><body>hi</body></html>", "text/html")},
    )
    assert res.status_code == 200
    page_id = res.json()["url"].split("//")[1].split(".")[0]

    with capture_logs() as cap:
        client.delete(
            f"/admin/pages/{page_id}",
            headers={"Authorization": "Bearer tok_carol_admin"},
        )
    deletions = [entry for entry in cap if entry.get("event") == "page.deleted"]
    assert len(deletions) == 1
    assert deletions[0]["actor"] == "carol"


def test_cleanup_trigger_attributes_db_admin(client):
    with Session(client.app.state.engine) as session:
        session.add(User(name="bob", token_hash=hash_token("tok_bob_admin"), is_admin=True))
        session.commit()

    with capture_logs() as cap:
        res = client.post(
            "/admin/cleanup/trigger",
            headers={"Authorization": "Bearer tok_bob_admin"},
        )
    assert res.status_code == 200
    runs = [entry for entry in cap if entry.get("event") == "cleanup.run"]
    assert len(runs) == 1
    assert runs[0]["triggered_by"] == "bob"


def test_list_pages_includes_user_name_and_collection_name(client):
    engine = client.app.state.engine
    with Session(engine) as session:
        user = User(name="testuser", token_hash=hash_token("tok_test_user"))
        session.add(user)
        session.flush()
        collection = Collection(name="testcol", user_id=user.id)
        session.add(collection)
        session.flush()
        page = Page(
            id="page001",
            token_hint="testuser",
            filename="test.html",
            user_id=user.id,
            collection_id=collection.id,
        )
        session.add(page)
        session.commit()

    res = client.get("/admin/pages", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 200
    pages = res.json()
    assert len(pages) == 1
    assert pages[0]["user_name"] == "testuser"
    assert pages[0]["collection_name"] == "testcol"


def test_list_pages_null_for_unowned(client):
    engine = client.app.state.engine
    with Session(engine) as session:
        page = Page(id="page002", token_hint="nouser", filename="orphan.html")
        session.add(page)
        session.commit()

    res = client.get("/admin/pages", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 200
    pages = res.json()
    assert len(pages) == 1
    assert pages[0]["user_name"] is None


def test_list_pages_null_for_uncollected(client):
    engine = client.app.state.engine
    with Session(engine) as session:
        user = User(name="lonely", token_hash=hash_token("tok_lonely"))
        session.add(user)
        session.flush()
        page = Page(
            id="page003",
            token_hint="lonely",
            filename="lonely.html",
            user_id=user.id,
        )
        session.add(page)
        session.commit()

    res = client.get("/admin/pages", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 200
    pages = res.json()
    assert len(pages) == 1
    assert pages[0]["collection_name"] is None
    assert pages[0]["user_name"] == "lonely"
