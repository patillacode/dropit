import structlog
from sqlmodel import Session, col, select

from app.models import CleanupRun, Page
from app.utils import delete_page_file, utcnow

logger = structlog.get_logger()

_MAX_HISTORY = 50


def delete_expired_pages(engine, data_dir: str, triggered_by: str = "scheduler") -> int:
    now = utcnow()
    with Session(engine) as session:
        expired = session.exec(
            select(Page).where(Page.expires_at.isnot(None), Page.expires_at < now)
        ).all()
        file_paths = [delete_page_file(page, session, data_dir) for page in expired]
        deleted = len(file_paths)
        session.commit()
        for file_path in file_paths:
            file_path.unlink(missing_ok=True)

        session.add(CleanupRun(deleted_count=deleted, triggered_by=triggered_by))
        session.commit()

        all_runs = session.exec(select(CleanupRun).order_by(col(CleanupRun.ran_at).asc())).all()
        excess = len(all_runs) - _MAX_HISTORY
        if excess > 0:
            for old_run in all_runs[:excess]:
                session.delete(old_run)
            session.commit()

    logger.info("cleanup.run", deleted=deleted, triggered_by=triggered_by)
    return deleted
