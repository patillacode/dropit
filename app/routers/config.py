from fastapi import APIRouter

from app.settings import get_settings

router = APIRouter()


@router.get("/config")
def get_config():
    settings = get_settings()
    admin_ttls = settings.ttl_list
    if "forever" not in admin_ttls:
        admin_ttls = admin_ttls + ["forever"]
    return {
        "allowed_ttls": admin_ttls,
        "user_ttls": settings.user_ttl_list,
        "default_ttl": settings.default_ttl,
        "max_upload_size": settings.max_upload_size,
    }
