from pathlib import Path

from fastapi import HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, func, select

from app.banner import inject_banner
from app.models import Page
from app.settings import get_settings
from app.utils import utcnow

def serve_page_content(page_id: str, session: Session) -> HTMLResponse:
    settings = get_settings()

    page = session.exec(select(Page).where(func.lower(Page.id) == page_id.lower())).first()
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    if page.expires_at is not None and page.expires_at < utcnow():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page has expired")

    file_path = Path(settings.data_dir) / "pages" / page.id
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    content = file_path.read_bytes()
    if settings.banner_enabled:
        content = inject_banner(
            content, base_url=f"{settings.content_scheme}://{settings.content_domain}"
        )
    return HTMLResponse(content=content)
