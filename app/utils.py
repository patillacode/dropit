from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlmodel import Session

if TYPE_CHECKING:
    from app.models import Page


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def format_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.isoformat() + "Z"


def delete_page_file(page: "Page", session: Session, data_dir: str | Path) -> Path:
    # Stage the DB row for deletion and return its file path. The caller commits,
    # then unlinks the returned path, so the file is only removed once the DB
    # deletion is durable.
    file_path = Path(data_dir) / "pages" / page.id
    session.delete(page)
    return file_path
