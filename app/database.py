from collections.abc import Generator
from pathlib import Path

from sqlalchemy import event, text
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

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return _engine


def _add_column_if_missing(conn, table: str, column: str, ddl_type: str) -> None:
    existing = {r[1] for r in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}
    if column not in existing:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def _create_index_if_missing(conn, name: str, table: str, columns: str) -> None:
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})"))


def _migration_1(engine) -> None:
    # Relax the original NOT NULL constraint on page.expires_at (rebuild table).
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(page)")).fetchall()
    if not rows:
        return
    expires_row = next((r for r in rows if r[1] == "expires_at"), None)
    if not expires_row or expires_row[3] == 0:
        return
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE page RENAME TO _page_bak"))
        conn.execute(
            text(
                "CREATE TABLE page ("
                "id TEXT NOT NULL PRIMARY KEY, "
                "expires_at DATETIME, "
                "token_hint TEXT NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO page (id, expires_at, token_hint) "
                "SELECT id, expires_at, token_hint FROM _page_bak"
            )
        )
        conn.execute(text("DROP TABLE _page_bak"))
        conn.commit()


def _migration_2(engine) -> None:
    # Add filename + created_at columns to page.
    with engine.connect() as conn:
        _add_column_if_missing(conn, "page", "filename", "TEXT")
        _add_column_if_missing(conn, "page", "created_at", "DATETIME")
        conn.commit()


def _migration_3(engine) -> None:
    # Add file_size column to page.
    with engine.connect() as conn:
        _add_column_if_missing(conn, "page", "file_size", "INTEGER")
        conn.commit()


def _migration_4(engine) -> None:
    # Add user_id + collection_id foreign keys to page.
    with engine.connect() as conn:
        _add_column_if_missing(conn, "page", "user_id", "INTEGER REFERENCES user(id)")
        _add_column_if_missing(conn, "page", "collection_id", "INTEGER REFERENCES collection(id)")
        conn.commit()


def _migration_5(engine) -> None:
    # Index expires_at — the cleanup job scans for expired pages on every run.
    with engine.connect() as conn:
        _create_index_if_missing(conn, "ix_page_expires_at", "page", "expires_at")
        conn.commit()


_MIGRATIONS = [_migration_1, _migration_2, _migration_3, _migration_4, _migration_5]


def _run_migrations(engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"))
        conn.commit()

        rows = conn.execute(text("SELECT version FROM schema_version")).fetchall()
        if not rows:
            page_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(page)")).fetchall()}
            # Fresh DB: create_all will build the schema, skip migrations.
            # Existing DB without version tracking: run all migrations (they're idempotent).
            current = len(_MIGRATIONS) if not page_cols else 0
            conn.execute(text("INSERT INTO schema_version (version) VALUES (:v)"), {"v": current})
            conn.commit()
        else:
            current = rows[0][0]

    for idx, migrate in enumerate(_MIGRATIONS, start=1):
        if idx > current:
            migrate(engine)
            with engine.connect() as conn:
                conn.execute(text("UPDATE schema_version SET version = :v"), {"v": idx})
                conn.commit()


def init_db(engine=None) -> None:
    if engine is None:
        engine = get_engine()
    _run_migrations(engine)
    SQLModel.metadata.create_all(engine)


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
