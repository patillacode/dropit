def test_config_returns_max_upload_size(client):
    res = client.get("/config")
    assert res.status_code == 200
    data = res.json()
    assert "max_upload_size" in data
    assert data["max_upload_size"] == 5_242_880
