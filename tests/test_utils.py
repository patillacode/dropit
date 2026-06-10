from datetime import UTC, datetime, timedelta, timezone

from app.utils import format_dt, utcnow


def test_utcnow_returns_naive_datetime():
    result = utcnow()
    assert isinstance(result, datetime)
    assert result.tzinfo is None


def test_utcnow_is_approximately_now():
    before = datetime.now(UTC).replace(tzinfo=None)
    result = utcnow()
    after = datetime.now(UTC).replace(tzinfo=None)
    assert before <= result <= after


def test_format_dt_none_returns_none():
    assert format_dt(None) is None


def test_format_dt_naive_appends_z():
    dt = datetime(2024, 6, 1, 12, 0, 0)
    result = format_dt(dt)
    assert result == "2024-06-01T12:00:00Z"


def test_format_dt_aware_appends_z():
    dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    result = format_dt(dt)
    assert result == "2024-06-01T12:00:00Z"


def test_format_dt_aware_non_utc_converts_to_utc():
    # +02:00 offset: 12:00 local = 10:00 UTC
    tz = timezone(timedelta(hours=2))
    dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=tz)
    result = format_dt(dt)
    assert result == "2024-06-01T10:00:00Z"


def test_format_dt_with_microseconds():
    dt = datetime(2024, 6, 1, 12, 0, 0, 123456)
    result = format_dt(dt)
    assert result == "2024-06-01T12:00:00.123456Z"


def test_delete_page_file_removes_file_and_db_row(tmp_path):
    from sqlmodel import Session, create_engine

    from app.models import Page
    from app.utils import delete_page_file

    engine = create_engine("sqlite:///:memory:", echo=False)
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(engine)

    page_id = "test1234"
    file_path = tmp_path / "pages" / page_id
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes(b"<h1>Test</h1>")

    with Session(engine) as session:
        page = Page(id=page_id, token_hint="test")
        session.add(page)
        session.commit()

        assert file_path.exists()
        delete_page_file(page, session, tmp_path)
        session.commit()

    assert not file_path.exists()

    with Session(engine) as session:
        found = session.get(Page, page_id)
        assert found is None

    engine.dispose()
