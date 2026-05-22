from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.database import get_session
from app.models import Page
from app.settings import get_settings

router = APIRouter(prefix="/admin")

_bearer = HTTPBearer()


def verify_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> None:
    settings = get_settings()
    if not settings.admin_token or credentials.credentials != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


@router.get("/pages", dependencies=[Depends(verify_admin)])
def list_pages(session: Session = Depends(get_session)):
    settings = get_settings()
    pages = session.exec(select(Page)).all()
    result = []
    for page in pages:
        file_path = Path(settings.data_dir) / "pages" / page.id
        size = file_path.stat().st_size if file_path.exists() else 0
        result.append(
            {
                "id": page.id,
                "url": f"{settings.base_url}/p/{page.id}",
                "token_hint": page.token_hint,
                "expires_at": page.expires_at.isoformat() if page.expires_at else None,
                "file_size": size,
            }
        )
    return result


@router.delete("/pages/{page_id}", dependencies=[Depends(verify_admin)])
def delete_page(page_id: str, session: Session = Depends(get_session)):
    settings = get_settings()
    page = session.exec(select(Page).where(Page.id == page_id)).first()
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    file_path = Path(settings.data_dir) / "pages" / page_id
    file_path.unlink(missing_ok=True)
    session.delete(page)
    session.commit()
    return {"deleted": page_id}
