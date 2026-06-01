from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

_TEMPLATES = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/")
def landing(request: Request):
    return _TEMPLATES.TemplateResponse(request, "index.html")


@router.get("/admin")
def admin_ui(request: Request):
    return _TEMPLATES.TemplateResponse(request, "admin.html")
