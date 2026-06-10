from app.models import Collection, User
from app.utils import format_dt


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "is_admin": user.is_admin,
        "created_at": format_dt(user.created_at),
    }


def serialize_collection(coll: Collection, page_count: int | None = None) -> dict:
    data = {
        "id": coll.id,
        "name": coll.name,
        "created_at": format_dt(coll.created_at),
    }
    if page_count is not None:
        data["page_count"] = page_count
    return data
