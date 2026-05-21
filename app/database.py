from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.settings import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_path = f"{settings.data_dir}/dropit.db"
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def init_db() -> None:
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
