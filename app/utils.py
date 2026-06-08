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


def delete_page_file(page: "Page", session: Session, data_dir: str | Path) -> None:
    file_path = Path(data_dir) / "pages" / page.id
    file_path.unlink(missing_ok=True)
    session.delete(page)
