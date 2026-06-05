def test_config_returns_max_upload_size(client):
    res = client.get("/config")
    assert res.status_code == 200
    data = res.json()
    assert "max_upload_size" in data
    assert data["max_upload_size"] == 5_242_880


def test_config_user_default_ttl_present(client):
    res = client.get("/config")
    assert res.status_code == 200
    assert "user_default_ttl" in res.json()


def test_config_user_default_ttl_equals_default_when_in_user_list(client):
    # Default env: ALLOWED_TTLS=1h,6h,24h,48h,7d  DEFAULT_TTL=24h  MAX_USER_TTL=24h
    # user_ttls = ["1h", "6h", "24h"] — default_ttl "24h" is present
    res = client.get("/config")
    data = res.json()
    assert data["user_default_ttl"] == data["default_ttl"]


def test_config_user_default_ttl_clamped_when_default_outside_user_list(client, monkeypatch):
    from app.settings import get_settings
    monkeypatch.setenv("DEFAULT_TTL", "7d")
    monkeypatch.setenv("MAX_USER_TTL", "24h")
    monkeypatch.setenv("ALLOWED_TTLS", "1h,6h,24h,48h,7d")
    get_settings.cache_clear()
    try:
        res = client.get("/config")
        data = res.json()
        assert data["default_ttl"] == "7d"
        assert data["user_default_ttl"] in data["user_ttls"]
        assert data["user_default_ttl"] != "7d"
        assert data["user_default_ttl"] == data["user_ttls"][0]
    finally:
        get_settings.cache_clear()
