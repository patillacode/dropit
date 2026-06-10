import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from sqlmodel import Session

from app.errors import error_response
from app.routers.pages import serve_page_content
from app.settings import get_settings

_RESERVED_SUBDOMAINS = {
    "www",
}


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        return response

    @app.middleware("http")
    async def content_subdomain_middleware(request: Request, call_next):
        settings = get_settings()
        host = request.headers.get("host", "").split(":")[0]
        content_host = settings.content_domain.split(":")[0]
        suffix = f".{content_host}"

        if (
            host != content_host
            and host.endswith(suffix)
            and not request.url.path.startswith("/static/")
        ):
            page_id = host[: -len(suffix)]
            if page_id in _RESERVED_SUBDOMAINS:
                return await call_next(request)
            with Session(request.app.state.engine) as session:
                try:
                    response = serve_page_content(page_id, session)
                except HTTPException as exc:
                    response = error_response(exc.detail)
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response

        return await call_next(request)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=uuid.uuid4().hex[:8])
        return await call_next(request)
