from collections.abc import Generator
from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.settings import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "dropit.db"
        _engine = create_engine(
            f"sqlite:///{db_path.resolve()}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def _migrate_schema(engine) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(page)")).fetchall()
    if not rows:
        return
    expires_row = next((r for r in rows if r[1] == "expires_at"), None)
    if not expires_row or expires_row[3] == 0:
        return
    # Column is NOT NULL — recreate table with nullable expires_at
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE page RENAME TO _page_bak"))
        conn.commit()
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO page (id, expires_at, token_hint) "
            "SELECT id, expires_at, token_hint FROM _page_bak"
        ))
        conn.execute(text("DROP TABLE _page_bak"))
        conn.commit()


def init_db() -> None:
    engine = get_engine()
    _migrate_schema(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
