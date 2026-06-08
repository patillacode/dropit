from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

import app.database as db_mod
from app.models import Page
from app.settings import get_settings


def test_create_and_retrieve_page(db_session: Session):
    page = Page(
        id="abc123",
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        token_hint="alice",
    )
    db_session.add(page)
    db_session.commit()

    result = db_session.exec(select(Page).where(Page.id == "abc123")).first()
    assert result is not None
    assert result.token_hint == "alice"


def test_page_id_unique(db_session: Session):
    p1 = Page(id="dup", expires_at=datetime(2099, 1, 1, tzinfo=UTC), token_hint="x")
    p2 = Page(id="dup", expires_at=datetime(2099, 1, 1, tzinfo=UTC), token_hint="y")
    db_session.add(p1)
    db_session.commit()
    db_session.expunge(p1)
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_get_engine_enables_wal(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()

    original_engine = db_mod._engine
    db_mod._engine = None

    try:
        engine = db_mod.get_engine()
        with engine.connect() as conn:
            mode = conn.execute(text("PRAGMA journal_mode")).scalar()
            timeout = conn.execute(text("PRAGMA busy_timeout")).scalar()
        assert mode == "wal"
        assert timeout == 5000
    finally:
        engine.dispose()
        db_mod._engine = original_engine
        get_settings.cache_clear()


def test_init_db_creates_schema_version(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    original = db_mod._engine
    db_mod._engine = None
    try:
        db_mod.init_db()
        engine = db_mod.get_engine()
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        assert version == 4
    finally:
        if db_mod._engine is not None:
            db_mod._engine.dispose()
        db_mod._engine = original
        get_settings.cache_clear()


def test_init_db_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    original = db_mod._engine
    db_mod._engine = None
    try:
        db_mod.init_db()
        db_mod.init_db()  # must not raise
        engine = db_mod.get_engine()
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        assert version == 4
    finally:
        if db_mod._engine is not None:
            db_mod._engine.dispose()
        db_mod._engine = original
        get_settings.cache_clear()


def test_run_migrations_upgrades_old_install():
    from sqlalchemy import create_engine as sa_create_engine
    from sqlmodel.pool import StaticPool

    engine = sa_create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Seed an old-style page table missing filename and created_at
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE page ("
                "id TEXT NOT NULL PRIMARY KEY, "
                "expires_at DATETIME, "
                "token_hint TEXT NOT NULL"
                ")"
            )
        )
        conn.commit()

    db_mod._run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        cols = {r[1] for r in conn.execute(text("PRAGMA table_info(page)")).fetchall()}

    assert version == 4
    assert "filename" in cols
    assert "created_at" in cols
    assert "file_size" in cols
    assert "user_id" in cols
    assert "collection_id" in cols
    engine.dispose()


def test_migration_1_skips_when_no_table(tmp_path):
    from sqlalchemy import create_engine as sa_engine

    from app.database import _migration_1

    engine = sa_engine(f"sqlite:///{tmp_path}/test.db")
    _migration_1(engine)  # must not raise
    engine.dispose()


def test_migration_1_migrates_not_null_expires_at(tmp_path):
    from sqlalchemy import create_engine as sa_engine
    from sqlalchemy import text

    from app.database import _migration_1

    engine = sa_engine(f"sqlite:///{tmp_path}/test.db")
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE page ("
                "id TEXT NOT NULL PRIMARY KEY, "
                "expires_at DATETIME NOT NULL, "
                "token_hint TEXT NOT NULL"
                ")"
            )
        )
        conn.commit()

    _migration_1(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(page)")).fetchall()
    expires_row = next(r for r in rows if r[1] == "expires_at")
    assert expires_row[3] == 0  # notnull == 0 means nullable after migration
    engine.dispose()


def test_get_session_yields_session():
    from app.database import get_session

    gen = get_session()
    session = next(gen)
    assert session is not None
    try:
        next(gen)
    except StopIteration:
        pass


def test_migration_4_adds_user_id_and_collection_id(tmp_path):
    from sqlalchemy import create_engine as sa_engine
    from sqlmodel.pool import StaticPool

    from app.database import _migration_4

    engine = sa_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE user ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "name TEXT NOT NULL, "
                "token_hash TEXT NOT NULL, "
                "is_admin INTEGER NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE collection ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "name TEXT NOT NULL, "
                "user_id INTEGER NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE page ("
                "id TEXT NOT NULL PRIMARY KEY, "
                "expires_at DATETIME, "
                "token_hint TEXT NOT NULL, "
                "filename TEXT, "
                "created_at DATETIME, "
                "file_size INTEGER"
                ")"
            )
        )
        conn.commit()

    _migration_4(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(page)")).fetchall()
    cols = {r[1] for r in rows}
    assert "user_id" in cols
    assert "collection_id" in cols
    engine.dispose()


def test_migration_4_is_idempotent():
    from sqlalchemy import create_engine as sa_engine
    from sqlmodel.pool import StaticPool

    from app.database import _migration_4

    engine = sa_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE user ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "name TEXT NOT NULL, "
                "token_hash TEXT NOT NULL, "
                "is_admin INTEGER NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE collection ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "name TEXT NOT NULL, "
                "user_id INTEGER NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE page ("
                "id TEXT NOT NULL PRIMARY KEY, "
                "expires_at DATETIME, "
                "token_hint TEXT NOT NULL, "
                "filename TEXT, "
                "created_at DATETIME, "
                "file_size INTEGER"
                ")"
            )
        )
        conn.commit()

    _migration_4(engine)
    _migration_4(engine)  # must not raise

    engine.dispose()


def test_migration_4_preserves_existing_pages():
    from datetime import UTC, datetime

    from sqlalchemy import create_engine as sa_engine
    from sqlmodel.pool import StaticPool

    from app.database import _migration_4

    engine = sa_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE user ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "name TEXT NOT NULL, "
                "token_hash TEXT NOT NULL, "
                "is_admin INTEGER NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE collection ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "name TEXT NOT NULL, "
                "user_id INTEGER NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE page ("
                "id TEXT NOT NULL PRIMARY KEY, "
                "expires_at DATETIME, "
                "token_hint TEXT NOT NULL, "
                "filename TEXT, "
                "created_at DATETIME, "
                "file_size INTEGER"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO page (id, expires_at, token_hint, filename, created_at, file_size) "
                "VALUES (:id, :exp, :hint, :fn, :ca, :fs)"
            ),
            {
                "id": "abc123",
                "exp": datetime(2099, 1, 1, tzinfo=UTC),
                "hint": "alice",
                "fn": "test.html",
                "ca": datetime(2026, 1, 1, tzinfo=UTC),
                "fs": 1024,
            },
        )
        conn.commit()

    _migration_4(engine)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, token_hint, filename, file_size FROM page WHERE id = 'abc123'")
        ).first()

    assert row is not None
    assert row[0] == "abc123"
    assert row[1] == "alice"
    assert row[2] == "test.html"
    assert row[3] == 1024
    engine.dispose()
