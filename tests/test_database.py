from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import Page


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
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
