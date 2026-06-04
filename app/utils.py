from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def format_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.isoformat() + "Z"
