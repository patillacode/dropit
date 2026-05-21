from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from app.models import Page


def delete_expired_pages(engine, data_dir: str) -> int:
    now = datetime.now(timezone.utc)
    deleted = 0
    with Session(engine) as session:
        expired = session.exec(select(Page).where(Page.expires_at < now)).all()
        for page in expired:
            file_path = Path(data_dir) / "pages" / page.id
            file_path.unlink(missing_ok=True)
            session.delete(page)
            deleted += 1
        session.commit()
    return deleted
