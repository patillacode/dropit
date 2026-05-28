from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.cleanup import delete_expired_pages
from app.database import get_engine, init_db
from app.routers import admin, config, health, landing, me, upload
from app.routers.pages import serve_page_content
from app.settings import get_settings

_ERROR_HTML = (Path(__file__).parent / "static" / "error.html").read_text()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()
    scheduler = BackgroundScheduler()
    job = scheduler.add_job(
        delete_expired_pages,
        "interval",
        hours=settings.cleanup_interval_hours,
        args=[get_engine(), settings.data_dir],
    )
    app.state.cleanup_job = job
    app.state.engine = get_engine()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(title="dropit", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.include_router(landing.router)
    app.include_router(config.router)
    app.include_router(health.router)
    app.include_router(me.router)
    app.include_router(upload.router)
    app.include_router(admin.router)

    @app.get("/{path:path}", include_in_schema=False)
    async def catch_all(path: str):
        html = _ERROR_HTML.replace("__TITLE__", "This page doesn't exist").replace(
            "__SUBTITLE__", "Nothing was ever uploaded here."
        )
        return HTMLResponse(content=html, status_code=404)

    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 404:
            if exc.detail == "Page has expired":
                title = "This page has expired"
                subtitle = "The link is no longer valid."
            else:
                title = "This page doesn't exist"
                subtitle = "Nothing was ever uploaded here."
            html = _ERROR_HTML.replace("__TITLE__", title).replace("__SUBTITLE__", subtitle)
            return HTMLResponse(content=html, status_code=404)
        return await default_http_exception_handler(request, exc)

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

        if host != content_host and host.endswith(suffix):
            page_id = host[: -len(suffix)]
            with Session(request.app.state.engine) as session:
                try:
                    response = serve_page_content(page_id, session)
                except HTTPException as exc:
                    if exc.detail == "Page has expired":
                        title = "This page has expired"
                        subtitle = "The link is no longer valid."
                    else:
                        title = "This page doesn't exist"
                        subtitle = "Nothing was ever uploaded here."
                    html = _ERROR_HTML.replace("__TITLE__", title).replace("__SUBTITLE__", subtitle)
                    response = HTMLResponse(content=html, status_code=404)
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response

        return await call_next(request)

    return app


app = create_app()
