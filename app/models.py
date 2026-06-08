from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.utils import utcnow


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=64, unique=True, index=True)
    token_hash: str = Field(max_length=64, unique=True, index=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)


class Collection(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=128)
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow)

    __table_args__ = (UniqueConstraint("name", "user_id"),)


class Page(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=8)
    expires_at: datetime | None = Field(default=None, nullable=True)
    token_hint: str = Field(max_length=64)
    filename: str | None = Field(default=None, nullable=True)
    created_at: datetime | None = Field(default=None, nullable=True)
    file_size: int | None = Field(default=None, nullable=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", nullable=True)
    collection_id: int | None = Field(default=None, foreign_key="collection.id", nullable=True)

    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at < utcnow()


class CleanupRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ran_at: datetime = Field(default_factory=utcnow)
    deleted_count: int
    triggered_by: str = Field(default="scheduler")
