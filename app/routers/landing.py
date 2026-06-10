from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response
from fastapi.templating import Jinja2Templates

router = APIRouter()
_TEMPLATES = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
_STATIC = Path(__file__).parent.parent / "static"

_ROBOTS_TXT = """\
User-agent: *
Allow: /$
Disallow: /admin
Disallow: /config
Disallow: /health
Disallow: /me
Disallow: /upload
Disallow: /users
Disallow: /static/
"""


@router.get("/robots.txt", include_in_schema=False)
def robots():
    return Response(content=_ROBOTS_TXT, media_type="text/plain")


@router.get("/")
def landing():
    return FileResponse(_STATIC / "landing.html")


@router.get("/upload")
def upload_ui(request: Request):
    return _TEMPLATES.TemplateResponse(request, "index.html")


@router.get("/admin")
def admin_ui(request: Request):
    return _TEMPLATES.TemplateResponse(request, "admin.html")


@router.get("/files")
def files_ui(request: Request):
    return _TEMPLATES.TemplateResponse(request, "files.html")
