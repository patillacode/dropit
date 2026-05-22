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
    if settings.admin_token and token == settings.admin_token:
        return TokenUser(name="admin", is_admin=True)
    name = settings.token_map.get(token)
    if name is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return TokenUser(name=name, is_admin=False)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    return get_current_user(credentials).name
