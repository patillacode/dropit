from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Page(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=8)
    expires_at: Optional[datetime] = Field(default=None, nullable=True)
    token_hint: str = Field(max_length=64)
