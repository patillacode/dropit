import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.auth import TokenUser, get_current_user
from app.database import get_session
from app.models import Page
from app.settings import get_settings, parse_ttl_duration

router = APIRouter()


def _generate_id(session: Session) -> str:
    for _ in range(10):
        candidate = secrets.token_urlsafe(6)
        existing = session.exec(select(Page).where(Page.id == candidate)).first()
        if existing is None:
            return candidate
    raise RuntimeError("Failed to generate unique page ID")


@router.post("/upload")
async def upload(
    file: UploadFile,
    ttl: str | None = None,
    user: TokenUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    settings = get_settings()

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

    content = await file.read()

    if len(content) > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large. Max size: {settings.max_upload_size} bytes",
        )

    if not is_html_ext:
        stripped = content.strip().lower()
        html_starts = (b"<!doctype", b"<html", b"<head", b"<body", b"<!--")
        if not any(stripped.startswith(s) for s in html_starts):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Only HTML files are accepted",
            )

    page_id = _generate_id(session)
    expires_at = (
        None
        if ttl_seconds is None
        else (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).replace(tzinfo=None)
    )

    pages_dir = Path(settings.data_dir) / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / page_id).write_bytes(content)

    page = Page(id=page_id, expires_at=expires_at, token_hint=user.name)
    session.add(page)
    session.commit()

    return {
        "url": f"https://{page_id}.{settings.content_domain}",
        "expires_at": expires_at.isoformat() if expires_at else None,
    }
