import pytest

from app.settings import Settings, parse_ttl_duration


def test_parse_ttl_duration_hours():
    assert parse_ttl_duration("1h") == 3600
    assert parse_ttl_duration("6h") == 21600
    assert parse_ttl_duration("24h") == 86400
    assert parse_ttl_duration("48h") == 172800


def test_parse_ttl_duration_days():
    assert parse_ttl_duration("7d") == 604800


def test_parse_ttl_duration_forever():
    assert parse_ttl_duration("forever") is None


def test_parse_ttl_duration_invalid():
    with pytest.raises(ValueError, match="Invalid TTL format"):
        parse_ttl_duration("5m")


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("BASE_URL", "http://localhost:8000")
    s = Settings()
    assert s.default_ttl == "24h"
    assert s.cleanup_interval_hours == 1
    assert s.max_upload_size == 5_242_880
    assert s.ttl_list == ["1h", "6h", "24h", "48h", "7d"]
