import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.auth import TokenUser, get_current_user, hash_token, require_admin, verify_token
from app.models import User
from app.settings import Settings


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(User(name="alice", token_hash=hash_token("tok_test123"), is_admin=False))
        s.commit()
        yield s
    engine.dispose()


def make_creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def settings_with(admin_token: str | None = None) -> Settings:
    return Settings(data_dir="/tmp", admin_token=admin_token)


def test_valid_token_returns_user(session, monkeypatch):
    monkeypatch.setattr("app.auth.get_settings", lambda: settings_with())
    user = get_current_user(make_creds("tok_test123"), session)
    assert user.name == "alice"
    assert user.is_admin is False
    assert user.user_id is not None
    assert verify_token(user) == "alice"


def test_invalid_token_raises_401(session, monkeypatch):
    monkeypatch.setattr("app.auth.get_settings", lambda: settings_with())
    with pytest.raises(HTTPException) as exc:
        get_current_user(make_creds("wrong_token"), session)
    assert exc.value.status_code == 401


def test_admin_token_is_recognized(session, monkeypatch):
    monkeypatch.setattr("app.auth.get_settings", lambda: settings_with(admin_token="secret_admin"))
    user = get_current_user(make_creds("secret_admin"), session)
    assert user.is_admin is True
    assert user.name == "admin"
    assert user.user_id is None


def test_require_admin_passes_for_admin():
    require_admin(TokenUser(name="admin", is_admin=True))  # must not raise


def test_require_admin_raises_403_for_non_admin():
    with pytest.raises(HTTPException) as exc:
        require_admin(TokenUser(name="alice", is_admin=False, user_id=1))
    assert exc.value.status_code == 403
