from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, col, select

from app.auth import TokenUser, require_admin
from app.cleanup import delete_expired_pages
from app.database import get_session
from app.models import CleanupRun, Page
from app.settings import get_settings
from app.utils import format_dt

logger = structlog.get_logger()

router = APIRouter(prefix="/admin")


@router.get("/pages", dependencies=[Depends(require_admin)])
def list_pages(session: Session = Depends(get_session)):
    settings = get_settings()
    pages = session.exec(select(Page)).all()
    return [
        {
            "id": page.id,
            "url": settings.page_url(page.id),
            "token_hint": page.token_hint,
            "expires_at": format_dt(page.expires_at),
            "file_size": page.file_size if page.file_size is not None else 0,
            "filename": page.filename,
            "created_at": format_dt(page.created_at),
        }
        for page in pages
    ]


@router.get("/cleanup/status", dependencies=[Depends(require_admin)])
def cleanup_status(request: Request, session: Session = Depends(get_session)):
    last_run = session.exec(select(CleanupRun).order_by(col(CleanupRun.ran_at).desc())).first()
    job = getattr(request.app.state, "cleanup_job", None)
    next_run = format_dt(job.next_run_time) if job else None
    return {
        "last_run": {
            "ran_at": format_dt(last_run.ran_at),
            "deleted_count": last_run.deleted_count,
            "triggered_by": last_run.triggered_by,
        }
        if last_run
        else None,
        "next_run": next_run,
    }


@router.get("/cleanup/history", dependencies=[Depends(require_admin)])
def cleanup_history(session: Session = Depends(get_session)):
    runs = session.exec(select(CleanupRun).order_by(col(CleanupRun.ran_at).desc())).all()
    return [
        {
            "id": run.id,
            "ran_at": format_dt(run.ran_at),
            "deleted_count": run.deleted_count,
            "triggered_by": run.triggered_by,
        }
        for run in runs
    ]


@router.post("/cleanup/trigger")
def trigger_cleanup(request: Request, user: TokenUser = Depends(require_admin)):
    settings = get_settings()
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Engine not available"
        )
    deleted = delete_expired_pages(engine, settings.data_dir, triggered_by=user.name)
    return {"deleted": deleted}


@router.delete("/pages/{page_id}")
def delete_page(
    page_id: str,
    user: TokenUser = Depends(require_admin),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    page = session.exec(select(Page).where(Page.id == page_id)).first()
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    file_path = Path(settings.data_dir) / "pages" / page_id
    file_path.unlink(missing_ok=True)
    session.delete(page)
    session.commit()
    logger.info("page.deleted", page_id=page_id, actor=user.name)
    return {"deleted": page_id}
