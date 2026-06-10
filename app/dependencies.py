from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.auth import TokenUser, get_db_user
from app.database import get_session
from app.models import Collection


def get_owned_collection(
    coll_id: int,
    user: TokenUser = Depends(get_db_user),
    session: Session = Depends(get_session),
) -> Collection:
    coll = session.get(Collection, coll_id)
    if coll is None or coll.user_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return coll
