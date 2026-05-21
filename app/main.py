from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routers import pages, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="dropit", lifespan=lifespan)
    app.include_router(upload.router)
    app.include_router(pages.router)
    return app


app = create_app()
