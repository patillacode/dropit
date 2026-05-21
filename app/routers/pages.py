from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import Page
from app.settings import get_settings

router = APIRouter()


@router.get("/p/{page_id}", response_class=HTMLResponse)
def serve_page(page_id: str, session: Session = Depends(get_session)):
    settings = get_settings()

    page = session.exec(select(Page).where(Page.id == page_id)).first()
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    if page.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page has expired")

    file_path = Path(settings.data_dir) / "pages" / page_id
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    return HTMLResponse(content=file_path.read_bytes())
