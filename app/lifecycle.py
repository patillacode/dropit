from contextlib import asynccontextmanager

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.cleanup import delete_expired_pages
from app.database import dispose_engine, get_engine, init_db
from app.settings import get_settings


def create_lifespan(engine=None):
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

    return lifespan
