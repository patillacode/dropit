from datetime import UTC, datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.cleanup import delete_expired_pages
from app.models import Page


def make_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


def test_cleanup_removes_expired(tmp_path):
    engine = make_engine()
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()

    expired_id = "exp001"
    live_id = "liv001"
    (pages_dir / expired_id).write_bytes(b"<h1>Old</h1>")
    (pages_dir / live_id).write_bytes(b"<h1>New</h1>")

    with Session(engine) as session:
        session.add(
            Page(
                id=expired_id,
                expires_at=datetime.now(UTC) - timedelta(hours=1),
                token_hint="alice",
            )
        )
        session.add(
            Page(
                id=live_id,
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                token_hint="alice",
            )
        )
        session.commit()

    deleted = delete_expired_pages(engine, str(tmp_path))

    assert deleted == 1
    with Session(engine) as session:
        remaining = session.exec(select(Page)).all()
        assert len(remaining) == 1
        assert remaining[0].id == live_id

    assert not (pages_dir / expired_id).exists()
    assert (pages_dir / live_id).exists()


def test_cleanup_tolerates_missing_file(tmp_path):
    engine = make_engine()
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()

    with Session(engine) as session:
        session.add(
            Page(
                id="ghost1",
                expires_at=datetime.now(UTC) - timedelta(hours=1),
                token_hint="alice",
            )
        )
        session.commit()

    delete_expired_pages(engine, str(tmp_path))

    with Session(engine) as session:
        remaining = session.exec(select(Page)).all()
        assert len(remaining) == 0
