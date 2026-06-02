from tests.conftest import USER_TOKEN


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
