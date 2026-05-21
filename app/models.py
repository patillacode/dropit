from datetime import datetime

from sqlmodel import Field, SQLModel


class Page(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=6)
    expires_at: datetime
    token_hint: str = Field(max_length=64)
