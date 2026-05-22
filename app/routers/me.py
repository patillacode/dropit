from fastapi import APIRouter, Depends

from app.auth import TokenUser, get_current_user

router = APIRouter()


@router.get("/me")
def me(user: TokenUser = Depends(get_current_user)):
    return {"name": user.name, "is_admin": user.is_admin}
