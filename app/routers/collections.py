import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, update
from sqlmodel import Session, select

from app.auth import TokenUser, get_db_user
from app.database import get_session
from app.dependencies import get_owned_collection
from app.limiter import limiter
from app.models import Collection, Page
from app.serializers import serialize_collection
from app.validators import clean_required_name

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
    return [serialize_collection(coll, count) for coll, count in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_collection(
    request: Request,
    payload: CollectionBody,
    user: TokenUser = Depends(get_db_user),
    session: Session = Depends(get_session),
):
    name = clean_required_name(payload.name, lower=True)
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
    return serialize_collection(coll)


@router.patch("/{coll_id}")
@limiter.limit("10/minute")
def rename_collection(
    request: Request,
    payload: CollectionBody,
    coll: Collection = Depends(get_owned_collection),
    session: Session = Depends(get_session),
):
    name = clean_required_name(payload.name, lower=True)
    if session.exec(
        select(Collection).where(
            Collection.user_id == coll.user_id,
            Collection.name == name,
            Collection.id != coll.id,
        )
    ).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Collection name already exists"
        )
    coll.name = name
    session.add(coll)
    session.commit()
    session.refresh(coll)
    logger.info("collection.renamed", collection_id=coll.id, user_id=coll.user_id)
    return serialize_collection(coll)


@router.delete("/{coll_id}")
@limiter.limit("10/minute")
def delete_collection(
    request: Request,
    coll: Collection = Depends(get_owned_collection),
    session: Session = Depends(get_session),
):
    session.exec(update(Page).where(Page.collection_id == coll.id).values(collection_id=None))
    coll_id = coll.id
    user_id = coll.user_id
    session.delete(coll)
    session.commit()
    logger.info("collection.deleted", collection_id=coll_id, user_id=user_id)
    return {"deleted": coll_id}
