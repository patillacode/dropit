from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.errors import error_response
from app.lifecycle import create_lifespan
from app.limiter import limiter
from app.logging import configure_logging
from app.middleware import register_middleware
from app.routers import admin, collections, config, health, landing, me, upload, users
from app.settings import get_settings


def create_app(engine=None) -> FastAPI:
    configure_logging(get_settings().log_level)

    app = FastAPI(title="dropit", lifespan=create_lifespan(engine))
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

    register_middleware(app)

    return app


app = create_app()
