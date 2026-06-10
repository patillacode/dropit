import structlog
from fastapi import HTTPException, UploadFile, status

from app.auth import TokenUser
from app.settings import Settings, parse_ttl_duration

logger = structlog.get_logger()

_HTML_STARTS = (b"<!doctype", b"<html", b"<head", b"<body", b"<!--")


def clean_required_name(raw: str, *, lower: bool = False) -> str:
    name = raw.strip()
    if lower:
        name = name.lower()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Name required"
        )
    return name


def validate_ttl(ttl: str | None, user: TokenUser, settings: Settings) -> tuple[str, int | None]:
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
    return effective_ttl, ttl_seconds


def validate_upload_filename(file: UploadFile) -> None:
    filename = file.filename or ""
    is_html_ext = filename.endswith(".html") or filename.endswith(".htm")
    is_html_ct = file.content_type in ("text/html", "application/octet-stream")
    if not is_html_ext and not is_html_ct:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Only HTML files are accepted"
        )


def validate_upload_content(content: bytes, user_name: str) -> None:
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning("upload.failure", reason="invalid_content", user=user_name)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only UTF-8 encoded HTML files are accepted",
        ) from None
    stripped = content.strip().lower()
    if not any(stripped.startswith(s) for s in _HTML_STARTS):
        logger.warning("upload.failure", reason="invalid_content", user=user_name)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Only HTML files are accepted"
        )
