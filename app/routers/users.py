import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import TokenUser, generate_token, get_current_user, hash_token, require_admin
from app.database import get_session
from app.models import Collection, Page, User
from app.serializers import serialize_user
from app.settings import get_settings
from app.token_ops import regenerate_token
from app.utils import delete_page_file
from app.validators import clean_required_name

logger = structlog.get_logger()

router = APIRouter(prefix="/admin/users", dependencies=[Depends(require_admin)])


class CreateUser(BaseModel):
    name: str
    is_admin: bool = False


@router.get("")
def list_users(session: Session = Depends(get_session)):
    users = session.exec(select(User).order_by(User.created_at)).all()
    return [serialize_user(user) for user in users]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUser, session: Session = Depends(get_session)):
    name = clean_required_name(payload.name)
    if name.lower() == "admin":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="'admin' is reserved for break-glass"
        )
    if session.exec(select(User).where(User.name == name)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Name already taken")
    token = generate_token()
    user = User(name=name, token_hash=hash_token(token), is_admin=payload.is_admin)
    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info("user.created", user_id=user.id, name=user.name, is_admin=user.is_admin)
    return {**serialize_user(user), "token": token}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: TokenUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user_id == current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete yourself")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    settings = get_settings()

    pages = session.exec(select(Page).where(Page.user_id == user_id)).all()
    file_paths = [delete_page_file(page, session, settings.data_dir) for page in pages]

    collections = session.exec(select(Collection).where(Collection.user_id == user_id)).all()
    for coll in collections:
        session.delete(coll)

    session.delete(user)
    session.commit()
    for file_path in file_paths:
        file_path.unlink(missing_ok=True)
    logger.info("user.deleted", user_id=user_id, actor=current_user.name)
    return {"deleted": user_id}


@router.post("/{user_id}/regenerate")
def regenerate_user_token(
    user_id: int,
    current_user: TokenUser = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    token = regenerate_token(user, session)
    logger.info("user.token_regenerated", user_id=user_id, actor=current_user.name)
    return {"token": token}
