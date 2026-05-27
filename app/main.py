from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.cleanup import delete_expired_pages
from app.database import get_engine, init_db
from app.routers import admin, config, health, landing, me, pages, upload
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
    app.include_router(pages.router)
    app.include_router(admin.router)

    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 404 and request.url.path.startswith("/p/"):
            if exc.detail == "Page has expired":
                title = "This page has expired"
                subtitle = "The link is no longer valid."
            else:
                title = "This page doesn't exist"
                subtitle = "Nothing was ever uploaded here."
            html = _ERROR_HTML.replace("__TITLE__", title).replace("__SUBTITLE__", subtitle)
            return HTMLResponse(content=html, status_code=404)
        return await default_http_exception_handler(request, exc)

    return app


app = create_app()
