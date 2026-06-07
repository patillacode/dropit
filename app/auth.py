import hashlib
import secrets
from dataclasses import dataclass

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.database import get_session
from app.models import User
from app.settings import get_settings

logger = structlog.get_logger()

_bearer = HTTPBearer()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token() -> str:
    return secrets.token_hex(16)


@dataclass
class TokenUser:
    name: str
    is_admin: bool
    user_id: int | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: Session = Depends(get_session),
) -> TokenUser:
    settings = get_settings()
    token = credentials.credentials
    if settings.admin_token and secrets.compare_digest(token, settings.admin_token):
        return TokenUser(name="admin", is_admin=True, user_id=None)
    user = session.exec(select(User).where(User.token_hash == hash_token(token))).first()
    if user is None:
        logger.warning("auth.failure", reason="invalid_token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return TokenUser(name=user.name, is_admin=user.is_admin, user_id=user.id)


def verify_token(user: TokenUser = Depends(get_current_user)) -> str:
    return user.name


def require_admin(user: TokenUser = Depends(get_current_user)) -> None:
    if not user.is_admin:
        logger.warning("auth.failure", reason="not_admin", user=user.name)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
