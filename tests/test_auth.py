import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import get_current_user, require_admin, verify_token
from app.settings import Settings, get_settings


def make_creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def make_settings(**kwargs):
    return Settings(
        upload_tokens="alice:tok_test123", base_url="http://localhost", data_dir="/tmp", **kwargs
    )


def test_valid_token_returns_name(monkeypatch):
    settings = make_settings()
    monkeypatch.setattr("app.auth.get_settings", lambda: settings)
    get_settings.cache_clear()
    assert verify_token(make_creds("tok_test123")) == "alice"


def test_invalid_token_raises_401(monkeypatch):
    settings = make_settings()
    monkeypatch.setattr("app.auth.get_settings", lambda: settings)
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        verify_token(make_creds("wrong_token"))
    assert exc.value.status_code == 401


def test_admin_token_is_recognized(monkeypatch):
    settings = make_settings(admin_token="secret_admin")
    monkeypatch.setattr("app.auth.get_settings", lambda: settings)
    get_settings.cache_clear()
    user = get_current_user(make_creds("secret_admin"))
    assert user.is_admin is True
    assert user.name == "admin"


def test_regular_token_is_not_admin(monkeypatch):
    settings = make_settings(admin_token="secret_admin")
    monkeypatch.setattr("app.auth.get_settings", lambda: settings)
    get_settings.cache_clear()
    user = get_current_user(make_creds("tok_test123"))
    assert user.is_admin is False
    assert user.name == "alice"


def test_require_admin_passes_for_admin_token(monkeypatch):
    settings = make_settings(admin_token="secret_admin")
    monkeypatch.setattr("app.auth.get_settings", lambda: settings)
    get_settings.cache_clear()
    require_admin(make_creds("secret_admin"))  # must not raise


def test_require_admin_raises_403_for_unknown_token(monkeypatch):
    settings = make_settings(admin_token="secret_admin")
    monkeypatch.setattr("app.auth.get_settings", lambda: settings)
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        require_admin(make_creds("totally_unknown"))
    assert exc.value.status_code == 403


def test_require_admin_raises_403_for_non_admin_token(monkeypatch):
    settings = make_settings(admin_token="secret_admin")
    monkeypatch.setattr("app.auth.get_settings", lambda: settings)
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        require_admin(make_creds("tok_test123"))
    assert exc.value.status_code == 403
