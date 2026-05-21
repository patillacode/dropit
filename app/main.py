from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.cleanup import delete_expired_pages
from app.database import get_engine, init_db
from app.routers import health, pages, upload
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        delete_expired_pages,
        "interval",
        hours=settings.cleanup_interval_hours,
        args=[get_engine(), settings.data_dir],
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(title="dropit", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(upload.router)
    app.include_router(pages.router)
    return app


app = create_app()
