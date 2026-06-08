import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, col, select

from app.auth import TokenUser, generate_token, get_current_user, hash_token
from app.database import get_session
from app.limiter import limiter
from app.models import Collection, Page, User
from app.settings import get_settings
from app.utils import format_dt

logger = structlog.get_logger()

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
    logger.info("token.regenerated", user_id=user.user_id, user=db_user.name)
    return {"token": token}


@router.get("/me/pages")
@limiter.limit("10/minute")
def my_pages(
    request: Request,
    user: TokenUser = Depends(get_current_user),
    session: Session = Depends(get_session),
    collection: str | None = None,
    uncollected: bool = False,
):
    settings = get_settings()
    stmt = (
        select(Page, Collection.name.label("collection_name"))
        .outerjoin(Collection, Page.collection_id == Collection.id)
        .where(Page.user_id == user.user_id)
    )
    if uncollected:
        stmt = stmt.where(Page.collection_id == None)  # noqa: E711
    elif collection:
        coll_name = collection.lower().strip()
        stmt = stmt.where(Collection.name == coll_name)
    stmt = stmt.order_by(col(Page.created_at).desc())
    rows = session.exec(stmt).all()
    return [
        {
            "url": settings.page_url(page.id),
            "filename": page.filename,
            "expires_at": format_dt(page.expires_at),
            "created_at": format_dt(page.created_at),
            "collection_id": page.collection_id,
            "collection_name": coll_name,
        }
        for page, coll_name in rows
    ]
