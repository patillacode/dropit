from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

_STATIC = Path(__file__).parent.parent / "static"


@router.get("/")
def landing():
    return FileResponse(_STATIC / "index.html")


@router.get("/admin")
def admin_ui():
    return FileResponse(_STATIC / "admin.html")
