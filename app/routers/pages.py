from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.models import Page
from app.settings import get_settings

def serve_page_content(page_id: str, session: Session) -> HTMLResponse:
    settings = get_settings()

    page = session.exec(select(Page).where(Page.id == page_id)).first()
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    if page.expires_at is not None and page.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page has expired")

    file_path = Path(settings.data_dir) / "pages" / page_id
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    return HTMLResponse(content=file_path.read_bytes())
