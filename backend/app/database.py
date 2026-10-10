from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine():
    return create_engine(
        get_settings().metadata_db_url,
        connect_args={"check_same_thread": False},
    )


engine = _engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_metadata_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
