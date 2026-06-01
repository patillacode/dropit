from sqlmodel import Session

from app.models import Page

ADMIN = {"Authorization": "Bearer admin_tok_xyz"}


def _alice_id(client) -> int:
    users = client.get("/admin/users", headers=ADMIN).json()
    return next(u["id"] for u in users if u["name"] == "alice")


def test_list_users_requires_admin(client):
    res = client.get("/admin/users", headers={"Authorization": "Bearer tok_test123"})
    assert res.status_code == 403


def test_list_users_shows_seeded_user(client):
    res = client.get("/admin/users", headers=ADMIN)
    assert res.status_code == 200
    names = [u["name"] for u in res.json()]
    assert "alice" in names
    assert all("token" not in u and "token_hash" not in u for u in res.json())


def test_create_user_returns_token_once_and_logs_in(client):
    res = client.post("/admin/users", headers=ADMIN, json={"name": "bob"})
    assert res.status_code == 201
    body = res.json()
    token = body["token"]
    assert body["name"] == "bob"
    assert body["is_admin"] is False

    # token is not present in the list response
    listed = client.get("/admin/users", headers=ADMIN).json()
    assert all("token" not in u for u in listed)

    # the new token authenticates
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["name"] == "bob"


def test_create_admin_user(client):
    res = client.post("/admin/users", headers=ADMIN, json={"name": "carol", "is_admin": True})
    assert res.status_code == 201
    token = res.json()["token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["is_admin"] is True


def test_create_duplicate_name_conflicts(client):
    res = client.post("/admin/users", headers=ADMIN, json={"name": "alice"})
    assert res.status_code == 409


def test_create_reserved_admin_name_conflicts(client):
    res = client.post("/admin/users", headers=ADMIN, json={"name": "admin"})
    assert res.status_code == 409


def test_regenerate_kills_old_token(client):
    bob = client.post("/admin/users", headers=ADMIN, json={"name": "bob"}).json()
    old_token = bob["token"]

    res = client.post(f"/admin/users/{bob['id']}/regenerate", headers=ADMIN)
    assert res.status_code == 200
    new_token = res.json()["token"]
    assert new_token != old_token

    assert client.get("/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    assert client.get("/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200


def test_regenerate_nonexistent_returns_404(client):
    res = client.post("/admin/users/99999/regenerate", headers=ADMIN)
    assert res.status_code == 404


def test_delete_user_keeps_their_pages(client, tmp_path):
    engine = client.app.state.engine
    (tmp_path / "pages" / "keep01").write_bytes(b"<h1>Hi</h1>")
    with Session(engine) as session:
        session.add(Page(id="keep01", expires_at=None, token_hint="alice"))
        session.commit()

    res = client.delete(f"/admin/users/{_alice_id(client)}", headers=ADMIN)
    assert res.status_code == 200

    pages = client.get("/admin/pages", headers=ADMIN).json()
    assert any(p["id"] == "keep01" and p["token_hint"] == "alice" for p in pages)


def test_delete_nonexistent_user_returns_404(client):
    res = client.delete("/admin/users/99999", headers=ADMIN)
    assert res.status_code == 404


def test_self_delete_blocked(client):
    created = client.post("/admin/users", headers=ADMIN, json={"name": "dave", "is_admin": True})
    token = created.json()["token"]
    dave_id = created.json()["id"]
    res = client.delete(f"/admin/users/{dave_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
