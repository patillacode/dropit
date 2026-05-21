import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import verify_token
from app.settings import Settings, get_settings


def make_creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_valid_token_returns_name(monkeypatch):
    settings = Settings(
        upload_tokens="alice:tok_test123",
        base_url="http://localhost",
        data_dir="/tmp",
    )
    monkeypatch.setattr("app.auth.get_settings", lambda: settings)
    get_settings.cache_clear()
    name = verify_token(make_creds("tok_test123"))
    assert name == "alice"


def test_invalid_token_raises_401(monkeypatch):
    settings = Settings(
        upload_tokens="alice:tok_test123",
        base_url="http://localhost",
        data_dir="/tmp",
    )
    monkeypatch.setattr("app.auth.get_settings", lambda: settings)
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        verify_token(make_creds("wrong_token"))
    assert exc.value.status_code == 401
