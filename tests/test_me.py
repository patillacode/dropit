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
