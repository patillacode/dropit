from fastapi import APIRouter

from app.settings import get_settings

router = APIRouter()


@router.get("/config")
def get_config():
    settings = get_settings()
    return {
        "allowed_ttls": settings.ttl_list,
        "user_ttls": settings.user_ttl_list,
        "default_ttl": settings.default_ttl,
    }
