import secrets
from datetime import timedelta
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlmodel import Session, select

from app.auth import TokenUser, get_current_user
from app.database import get_session
from app.limiter import limiter
from app.models import Collection, Page
from app.settings import get_settings, parse_ttl_duration
from app.utils import format_dt, utcnow

logger = structlog.get_logger()

router = APIRouter()


def _generate_id(session: Session) -> str:
    for _ in range(10):
        candidate = secrets.token_hex(4)
        existing = session.exec(select(Page).where(Page.id == candidate)).first()
        if existing is None:
            return candidate
    raise RuntimeError("Failed to generate unique page ID")


@router.post("/upload")
@limiter.limit("5/minute")
async def upload(
    request: Request,
    file: UploadFile,
    ttl: str | None = None,
    collection: str | None = None,
    user: TokenUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    settings = get_settings()

    content_length_header = request.headers.get("content-length")
    if content_length_header is not None:
        try:
            if int(content_length_header) > settings.max_upload_size:
                logger.warning(
                    "upload.failure",
                    reason="too_large",
                    user=user.name,
                    size=int(content_length_header),
                )
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"File too large. Max size: {settings.max_upload_size} bytes",
                )
        except ValueError:
            pass

    effective_ttl = ttl or settings.default_ttl
    if effective_ttl != "forever" and effective_ttl not in settings.ttl_list:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid TTL. Allowed: {settings.ttl_list}",
        )

    ttl_seconds = parse_ttl_duration(effective_ttl)

    if not user.is_admin:
        if ttl_seconds is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="forever TTL requires admin token",
            )
        max_secs = parse_ttl_duration(settings.max_user_ttl)
        if max_secs is not None and ttl_seconds > max_secs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"TTL exceeds maximum allowed for your token ({settings.max_user_ttl})",
            )

    filename = file.filename or ""
    is_html_ext = filename.endswith(".html") or filename.endswith(".htm")
    is_html_ct = file.content_type in ("text/html", "application/octet-stream")
    if not is_html_ext and not is_html_ct:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only HTML files are accepted",
        )

    buf = bytearray()
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        buf += chunk
        if len(buf) > settings.max_upload_size:
            logger.warning(
                "upload.failure",
                reason="too_large",
                user=user.name,
                size=len(buf),
            )
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File too large. Max size: {settings.max_upload_size} bytes",
            )
    content = bytes(buf)

    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning("upload.failure", reason="invalid_content", user=user.name)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only UTF-8 encoded HTML files are accepted",
        ) from None

    stripped = content.strip().lower()
    html_starts = (b"<!doctype", b"<html", b"<head", b"<body", b"<!--")
    if not any(stripped.startswith(s) for s in html_starts):
        logger.warning("upload.failure", reason="invalid_content", user=user.name)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only HTML files are accepted",
        )

    collection_id = None
    collection_name = None
    if collection:
        if user.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Collections require a DB user token",
            )
        collection_name = collection.lower().strip()
        if not collection_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Collection name cannot be empty",
            )
        coll = session.exec(
            select(Collection).where(
                Collection.name == collection_name,
                Collection.user_id == user.user_id,
            )
        ).first()
        if coll is None:
            coll = Collection(name=collection_name, user_id=user.user_id)
            session.add(coll)
            session.flush()
        collection_id = coll.id

    try:
        page_id = _generate_id(session)
    except RuntimeError:
        logger.error("upload.failure", reason="id_collision_exhausted", user=user.name)
        raise
    expires_at = None if ttl_seconds is None else utcnow() + timedelta(seconds=ttl_seconds)

    pages_dir = Path(settings.data_dir) / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / page_id).write_bytes(content)

    page = Page(
        id=page_id,
        expires_at=expires_at,
        token_hint=user.name,
        filename=filename or None,
        created_at=utcnow(),
        file_size=len(content),
        user_id=user.user_id,
        collection_id=collection_id,
    )
    session.add(page)
    session.commit()

    logger.info(
        "upload.success",
        page_id=page_id,
        user=user.name,
        size=len(content),
        ttl=effective_ttl,
        collection=collection_name,
    )

    return {
        "url": settings.page_url(page_id),
        "expires_at": format_dt(expires_at),
        "collection": collection_name,
    }
