import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlmodel import Session

from app.cleanup import delete_expired_pages
from app.database import dispose_engine, get_engine, init_db
from app.errors import error_response
from app.limiter import limiter
from app.logging import configure_logging
from app.routers import admin, collections, config, health, landing, me, upload, users
from app.routers.pages import serve_page_content
from app.settings import get_settings

_RESERVED_SUBDOMAINS = {
    "www",
}


def create_app(engine=None) -> FastAPI:
    configure_logging(get_settings().log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _engine = engine if engine is not None else get_engine()
        init_db(_engine)
        settings = get_settings()
        scheduler = BackgroundScheduler()
        job = scheduler.add_job(
            delete_expired_pages,
            "interval",
            hours=settings.cleanup_interval_hours,
            args=[_engine, settings.data_dir],
        )
        app.state.cleanup_job = job
        app.state.engine = _engine
        scheduler.start()
        structlog.get_logger().info("app.startup", log_level=settings.log_level)
        yield
        scheduler.shutdown(wait=False)
        dispose_engine()
        structlog.get_logger().info("app.shutdown")

    app = FastAPI(title="dropit", lifespan=lifespan)
    app.state.limiter = limiter

    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        response = JSONResponse(
            {"detail": "Too many requests — please slow down and try again shortly"},
            status_code=429,
        )
        response = app.state.limiter._inject_headers(response, request.state.view_rate_limit)
        return response

    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.include_router(landing.router)
    app.include_router(config.router)
    app.include_router(health.router)
    app.include_router(me.router)
    app.include_router(upload.router)
    app.include_router(collections.router)
    app.include_router(admin.router)
    app.include_router(users.router)

    @app.get("/{path:path}", include_in_schema=False)
    async def catch_all(path: str):
        return error_response("not found")

    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 404:
            return error_response(exc.detail)
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

    return app


app = create_app()
