from tests.conftest import ADMIN_TOKEN, USER_TOKEN


def test_me_valid_token(client):
    res = client.get("/me", headers={"Authorization": "Bearer tok_test123"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "alice"
    assert data["is_admin"] is False


def test_me_admin_token(client):
    res = client.get("/me", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "admin"
    assert data["is_admin"] is True


def test_me_invalid_token(client):
    res = client.get("/me", headers={"Authorization": "Bearer bad_token"})
    assert res.status_code == 401


def test_me_regenerate_swaps_token(client):
    res = client.post("/me/regenerate", headers={"Authorization": "Bearer tok_test123"})
    assert res.status_code == 200
    new_token = res.json()["token"]
    assert new_token != "tok_test123"

    # old token is dead, new token works
    assert client.get("/me", headers={"Authorization": "Bearer tok_test123"}).status_code == 401
    res_new = client.get("/me", headers={"Authorization": f"Bearer {new_token}"})
    assert res_new.status_code == 200
    assert res_new.json()["name"] == "alice"


def test_me_regenerate_breakglass_rejected(client):
    res = client.post("/me/regenerate", headers={"Authorization": "Bearer admin_tok_xyz"})
    assert res.status_code == 400


def test_me_rate_limited(client):
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}
    for _ in range(5):
        r = client.get("/me", headers=headers)
        assert r.status_code == 200
    r = client.get("/me", headers=headers)
    assert r.status_code == 429
    assert r.json()["detail"] == "Too many requests — please slow down and try again shortly"


def test_regenerate_rate_limited(client):
    token = USER_TOKEN
    for _ in range(2):
        r = client.post("/me/regenerate", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        token = r.json()["token"]
    r = client.post("/me/regenerate", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 429
    assert r.json()["detail"] == "Too many requests — please slow down and try again shortly"


def test_regenerate_token_user_not_in_db(client):
    from app.auth import TokenUser, get_current_user

    async def ghost_user():
        return TokenUser(name="ghost", is_admin=False, user_id=99999)

    client.app.dependency_overrides[get_current_user] = ghost_user
    try:
        res = client.post(
            "/me/regenerate",
            headers={"Authorization": "Bearer anything"},
        )
        assert res.status_code == 401
        assert "Invalid token" in res.json()["detail"]
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)


def test_my_pages_empty(client):
    res = client.get("/me/pages", headers={"Authorization": f"Bearer {USER_TOKEN}"})
    assert res.status_code == 200
    assert res.json() == []


def test_my_pages_requires_auth(client):
    res = client.get("/me/pages")
    assert res.status_code == 401


def test_my_pages_returns_own_uploads(client):
    content = b"<!doctype html><html><body>hi</body></html>"
    client.post(
        "/upload",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        files={"file": ("test.html", content, "text/html")},
    )
    res = client.get("/me/pages", headers={"Authorization": f"Bearer {USER_TOKEN}"})
    assert res.status_code == 200
    pages = res.json()
    assert len(pages) == 1
    assert pages[0]["filename"] == "test.html"
    assert "url" in pages[0]
    assert "expires_at" in pages[0]
    assert "created_at" in pages[0]


def test_my_pages_excludes_other_users(client):
    content = b"<!doctype html><html><body>admin page</body></html>"
    client.post(
        "/upload",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        files={"file": ("admin.html", content, "text/html")},
    )
    res = client.get("/me/pages", headers={"Authorization": f"Bearer {USER_TOKEN}"})
    assert res.status_code == 200
    assert res.json() == []


def test_my_pages_sorted_newest_first(client):
    from datetime import UTC, datetime, timedelta

    from sqlmodel import Session

    from app.models import Page

    older = (datetime.now(UTC) - timedelta(hours=1)).replace(tzinfo=None)
    newer = datetime.now(UTC).replace(tzinfo=None)

    with Session(client.app.state.engine) as session:
        session.add(Page(id="old00001", token_hint="alice", filename="old.html", created_at=older))
        session.add(Page(id="new00001", token_hint="alice", filename="new.html", created_at=newer))
        session.commit()

    res = client.get("/me/pages", headers={"Authorization": f"Bearer {USER_TOKEN}"})
    pages = res.json()
    assert len(pages) == 2
    assert pages[0]["filename"] == "new.html"
    assert pages[1]["filename"] == "old.html"


def test_my_pages_rate_limited(client):
    headers = {"Authorization": f"Bearer {USER_TOKEN}"}
    for _ in range(10):
        r = client.get("/me/pages", headers=headers)
        assert r.status_code == 200
    r = client.get("/me/pages", headers=headers)
    assert r.status_code == 429
    assert r.json()["detail"] == "Too many requests — please slow down and try again shortly"
