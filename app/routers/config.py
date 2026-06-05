from fastapi import APIRouter

from app.settings import get_settings

router = APIRouter()


@router.get("/config")
def get_config():
    settings = get_settings()
    admin_ttls = settings.ttl_list
    if "forever" not in admin_ttls:
        admin_ttls = admin_ttls + ["forever"]
    user_ttls = settings.user_ttl_list
    user_default = (
        settings.default_ttl
        if settings.default_ttl in user_ttls
        else (user_ttls[0] if user_ttls else settings.default_ttl)
    )
    return {
        "allowed_ttls": admin_ttls,
        "user_ttls": user_ttls,
        "default_ttl": settings.default_ttl,
        "user_default_ttl": user_default,
        "max_upload_size": settings.max_upload_size,
    }
