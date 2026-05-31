import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.settings import get_settings

_bearer = HTTPBearer()


@dataclass
class TokenUser:
    name: str
    is_admin: bool


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> TokenUser:
    settings = get_settings()
    token = credentials.credentials
    if settings.admin_token and secrets.compare_digest(token, settings.admin_token):
        return TokenUser(name="admin", is_admin=True)
    name = None
    for stored_token, stored_name in settings.token_map.items():
        if secrets.compare_digest(token, stored_token):
            name = stored_name
            break
    if name is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return TokenUser(name=name, is_admin=False)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    return get_current_user(credentials).name


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> None:
    try:
        user = get_current_user(credentials)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        ) from None
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
