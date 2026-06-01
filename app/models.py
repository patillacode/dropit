from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=64, unique=True, index=True)
    token_hash: str = Field(max_length=64, unique=True, index=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))


class Page(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=8)
    expires_at: datetime | None = Field(default=None, nullable=True)
    token_hint: str = Field(max_length=64)
    filename: str | None = Field(default=None, nullable=True)
    created_at: datetime | None = Field(default=None, nullable=True)


class CleanupRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ran_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    deleted_count: int
    triggered_by: str = Field(default="scheduler")
