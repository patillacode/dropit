import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, update
from sqlmodel import Session, select

from app.auth import TokenUser, get_db_user
from app.database import get_session
from app.limiter import limiter
from app.models import Collection, Page
from app.utils import format_dt

logger = structlog.get_logger()

router = APIRouter(prefix="/collections")


class CollectionBody(BaseModel):
    name: str


@router.get("")
@limiter.limit("30/minute")
def list_collections(
    request: Request,
    user: TokenUser = Depends(get_db_user),
    session: Session = Depends(get_session),
):
    stmt = (
        select(Collection, func.count(Page.id).label("page_count"))
        .outerjoin(Page, (Page.collection_id == Collection.id))
        .where(Collection.user_id == user.user_id)
        .group_by(Collection.id)
        .order_by(Collection.created_at)
    )
    rows = session.exec(stmt).all()
    return [
        {
            "id": coll.id,
            "name": coll.name,
            "created_at": format_dt(coll.created_at),
            "page_count": count,
        }
        for coll, count in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_collection(
    request: Request,
    payload: CollectionBody,
    user: TokenUser = Depends(get_db_user),
    session: Session = Depends(get_session),
):
    name = payload.name.lower().strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name required"
        )
    if session.exec(
        select(Collection).where(Collection.user_id == user.user_id, Collection.name == name)
    ).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Collection name already exists"
        )
    coll = Collection(name=name, user_id=user.user_id)
    session.add(coll)
    session.commit()
    session.refresh(coll)
    logger.info("collection.created", collection_id=coll.id, user_id=user.user_id)
    return {"id": coll.id, "name": coll.name, "created_at": format_dt(coll.created_at)}


@router.patch("/{coll_id}")
@limiter.limit("10/minute")
def rename_collection(
    request: Request,
    coll_id: int,
    payload: CollectionBody,
    user: TokenUser = Depends(get_db_user),
    session: Session = Depends(get_session),
):
    coll = session.get(Collection, coll_id)
    if coll is None or coll.user_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    name = payload.name.lower().strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name required"
        )
    if session.exec(
        select(Collection).where(
            Collection.user_id == user.user_id,
            Collection.name == name,
            Collection.id != coll_id,
        )
    ).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Collection name already exists"
        )
    coll.name = name
    session.add(coll)
    session.commit()
    session.refresh(coll)
    logger.info("collection.renamed", collection_id=coll.id, user_id=user.user_id)
    return {"id": coll.id, "name": coll.name, "created_at": format_dt(coll.created_at)}


@router.delete("/{coll_id}")
@limiter.limit("10/minute")
def delete_collection(
    request: Request,
    coll_id: int,
    user: TokenUser = Depends(get_db_user),
    session: Session = Depends(get_session),
):
    coll = session.get(Collection, coll_id)
    if coll is None or coll.user_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    session.exec(update(Page).where(Page.collection_id == coll_id).values(collection_id=None))
    session.delete(coll)
    session.commit()
    logger.info("collection.deleted", collection_id=coll_id, user_id=user.user_id)
    return {"deleted": coll_id}
