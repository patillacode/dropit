import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.auth import hash_token
from app.database import get_session
from app.main import create_app
from app.models import Page, User
from app.routers import collections as collections_router
from app.settings import get_settings
from tests.conftest import ADMIN_TOKEN, USER_TOKEN

HEADERS = {"Authorization": f"Bearer {USER_TOKEN}"}
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture(name="client")
def client_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    get_settings.cache_clear()
    (tmp_path / "pages").mkdir()

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(name="alice", token_hash=hash_token(USER_TOKEN), is_admin=False))
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app = create_app(engine=engine)
    # Insert collections routes before the catch_all so GET /collections resolves correctly
    *before_catchall, catch_all_route = app.router.routes
    app.router.routes = before_catchall
    app.include_router(collections_router.router)
    app.router.routes.append(catch_all_route)
    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as c:
        yield c


def _create_bob(client):
    r = client.post("/admin/users", json={"name": "bob"}, headers=ADMIN_HEADERS)
    assert r.status_code == 201
    return r.json()["token"]


def test_break_glass_401(client):
    r = client.get("/collections", headers=ADMIN_HEADERS)
    assert r.status_code == 401


def test_list_empty(client):
    r = client.get("/collections", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []


def test_create(client):
    r = client.post("/collections", json={"name": "work"}, headers=HEADERS)
    assert r.status_code == 201
    d = r.json()
    assert d["name"] == "work"
    assert "id" in d
    assert "created_at" in d


def test_create_normalizes_lowercase(client):
    r = client.post("/collections", json={"name": "Work"}, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["name"] == "work"


def test_create_duplicate_409(client):
    client.post("/collections", json={"name": "work"}, headers=HEADERS)
    r = client.post("/collections", json={"name": "work"}, headers=HEADERS)
    assert r.status_code == 409


def test_create_same_name_different_user(client):
    bob_token = _create_bob(client)
    client.post("/collections", json={"name": "work"}, headers=HEADERS)
    bob_headers = {"Authorization": f"Bearer {bob_token}"}
    r = client.post("/collections", json={"name": "work"}, headers=bob_headers)
    assert r.status_code == 201


def test_rename(client):
    coll_id = client.post("/collections", json={"name": "old"}, headers=HEADERS).json()["id"]
    r = client.patch(f"/collections/{coll_id}", json={"name": "NEW"}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["name"] == "new"


def test_rename_other_user_404(client):
    bob_token = _create_bob(client)
    coll_id = client.post("/collections", json={"name": "mine"}, headers=HEADERS).json()["id"]
    r = client.patch(
        f"/collections/{coll_id}",
        json={"name": "stolen"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert r.status_code == 404


def test_rename_not_found_404(client):
    r = client.patch("/collections/999", json={"name": "x"}, headers=HEADERS)
    assert r.status_code == 404


def test_rename_conflict_409(client):
    client.post("/collections", json={"name": "alpha"}, headers=HEADERS)
    coll_id = client.post("/collections", json={"name": "beta"}, headers=HEADERS).json()["id"]
    r = client.patch(f"/collections/{coll_id}", json={"name": "alpha"}, headers=HEADERS)
    assert r.status_code == 409


def test_rename_empty_name_422(client):
    coll_id = client.post("/collections", json={"name": "x"}, headers=HEADERS).json()["id"]
    r = client.patch(f"/collections/{coll_id}", json={"name": ""}, headers=HEADERS)
    assert r.status_code == 422


def test_delete(client):
    coll_id = client.post("/collections", json={"name": "temp"}, headers=HEADERS).json()["id"]
    r = client.delete(f"/collections/{coll_id}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == {"deleted": coll_id}


def test_delete_nulls_page_collection_id(client):
    coll_id = client.post("/collections", json={"name": "mine"}, headers=HEADERS).json()["id"]
    engine = client.app.state.engine
    with Session(engine) as session:
        session.add(Page(id="test1234", token_hint="alice", collection_id=coll_id))
        session.commit()
    client.delete(f"/collections/{coll_id}", headers=HEADERS)
    with Session(engine) as session:
        page = session.get(Page, "test1234")
        assert page.collection_id is None


def test_delete_other_user_404(client):
    bob_token = _create_bob(client)
    coll_id = client.post("/collections", json={"name": "mine"}, headers=HEADERS).json()["id"]
    r = client.delete(f"/collections/{coll_id}", headers={"Authorization": f"Bearer {bob_token}"})
    assert r.status_code == 404


def test_delete_not_found_404(client):
    r = client.delete("/collections/999", headers=HEADERS)
    assert r.status_code == 404


def test_page_count(client):
    coll_id = client.post("/collections", json={"name": "counted"}, headers=HEADERS).json()["id"]
    assert client.get("/collections", headers=HEADERS).json()[0]["page_count"] == 0

    engine = client.app.state.engine
    with Session(engine) as session:
        session.add(Page(id="pagetest", token_hint="alice", collection_id=coll_id))
        session.commit()

    assert client.get("/collections", headers=HEADERS).json()[0]["page_count"] == 1


def test_empty_name_422(client):
    r = client.post("/collections", json={"name": ""}, headers=HEADERS)
    assert r.status_code == 422


def test_whitespace_name_422(client):
    r = client.post("/collections", json={"name": "   "}, headers=HEADERS)
    assert r.status_code == 422
