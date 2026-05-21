import pytest

from app.settings import Settings, parse_tokens, parse_ttl_duration


def test_parse_tokens_named():
    result = parse_tokens("alice:tok_abc,bob:tok_xyz")
    assert result == {"tok_abc": "alice", "tok_xyz": "bob"}


def test_parse_tokens_unnamed():
    result = parse_tokens("tok_abc,tok_xyz")
    assert result == {"tok_abc": "tok_abc", "tok_xyz": "tok_xyz"}


def test_parse_ttl_duration_hours():
    assert parse_ttl_duration("1h") == 3600
    assert parse_ttl_duration("6h") == 21600
    assert parse_ttl_duration("24h") == 86400
    assert parse_ttl_duration("48h") == 172800


def test_parse_ttl_duration_days():
    assert parse_ttl_duration("7d") == 604800


def test_parse_ttl_duration_invalid():
    with pytest.raises(ValueError, match="Invalid TTL format"):
        parse_ttl_duration("5m")


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("UPLOAD_TOKENS", "alice:tok_abc")
    monkeypatch.setenv("BASE_URL", "http://localhost:52031")
    s = Settings()
    assert s.default_ttl == "24h"
    assert s.cleanup_interval_hours == 1
    assert s.max_upload_size == 5_242_880
    assert s.allowed_ttls == ["1h", "6h", "24h", "48h", "7d"]
