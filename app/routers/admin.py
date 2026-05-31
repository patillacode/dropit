from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, col, select

from app.cleanup import delete_expired_pages
from app.database import get_session
from app.models import CleanupRun, Page
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
                "url": settings.page_url(page.id),
                "token_hint": page.token_hint,
                "expires_at": page.expires_at.isoformat() if page.expires_at else None,
                "file_size": size,
                "filename": page.filename,
                "created_at": page.created_at.isoformat() if page.created_at else None,
            }
        )
    return result


@router.get("/cleanup/status", dependencies=[Depends(verify_admin)])
def cleanup_status(request: Request, session: Session = Depends(get_session)):
    last_run = session.exec(select(CleanupRun).order_by(col(CleanupRun.ran_at).desc())).first()
    job = getattr(request.app.state, "cleanup_job", None)
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {
        "last_run": {
            "ran_at": last_run.ran_at.isoformat(),
            "deleted_count": last_run.deleted_count,
            "triggered_by": last_run.triggered_by,
        }
        if last_run
        else None,
        "next_run": next_run,
    }


@router.get("/cleanup/history", dependencies=[Depends(verify_admin)])
def cleanup_history(session: Session = Depends(get_session)):
    runs = session.exec(select(CleanupRun).order_by(col(CleanupRun.ran_at).desc())).all()
    return [
        {
            "id": run.id,
            "ran_at": run.ran_at.isoformat(),
            "deleted_count": run.deleted_count,
            "triggered_by": run.triggered_by,
        }
        for run in runs
    ]


@router.post("/cleanup/trigger", dependencies=[Depends(verify_admin)])
def trigger_cleanup(request: Request):
    settings = get_settings()
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Engine not available"
        )
    deleted = delete_expired_pages(engine, settings.data_dir, triggered_by="admin")
    return {"deleted": deleted}


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
