import pytest
from pydantic import ValidationError

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
    monkeypatch.delenv("DEFAULT_TTL", raising=False)
    monkeypatch.delenv("ALLOWED_TTLS", raising=False)
    s = Settings(_env_file=None)
    assert s.default_ttl == "24h"
    assert s.cleanup_interval_hours == 1
    assert s.max_upload_size == 5_242_880
    assert s.ttl_list == ["1h", "6h", "24h", "48h", "7d"]


def test_invalid_allowed_ttls_raises_at_startup(monkeypatch):
    monkeypatch.setenv("ALLOWED_TTLS", "1h,bad_value")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_default_ttl_raises_at_startup(monkeypatch):
    monkeypatch.setenv("DEFAULT_TTL", "5m")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_max_user_ttl_raises_at_startup(monkeypatch):
    monkeypatch.setenv("MAX_USER_TTL", "bad")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_valid_ttl_config_does_not_raise(monkeypatch):
    monkeypatch.setenv("ALLOWED_TTLS", "1h,24h,7d,forever")
    monkeypatch.setenv("DEFAULT_TTL", "24h")
    monkeypatch.setenv("MAX_USER_TTL", "24h")
    s = Settings(_env_file=None)
    assert s.ttl_list == ["1h", "24h", "7d", "forever"]


def test_banner_enabled_default(monkeypatch):
    monkeypatch.delenv("BANNER_ENABLED", raising=False)
    s = Settings(_env_file=None)
    assert s.banner_enabled is True


def test_banner_enabled_can_be_disabled(monkeypatch):
    monkeypatch.setenv("BANNER_ENABLED", "false")
    s = Settings(_env_file=None)
    assert s.banner_enabled is False
