from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.auth import TokenUser, generate_token, get_current_user, hash_token
from app.database import get_session
from app.limiter import limiter
from app.models import User

router = APIRouter()


@router.get("/me")
@limiter.limit("5/minute")
def me(request: Request, user: TokenUser = Depends(get_current_user)):
    return {"name": user.name, "is_admin": user.is_admin}


@router.post("/me/regenerate")
@limiter.limit("2/minute")
def regenerate_own_token(
    request: Request,
    user: TokenUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="break-glass token is managed via ADMIN_TOKEN and cannot be regenerated",
        )
    db_user = session.get(User, user.user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    token = generate_token()
    db_user.token_hash = hash_token(token)
    session.add(db_user)
    session.commit()
    return {"token": token}
