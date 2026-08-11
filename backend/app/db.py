from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base


def _sqlite_url(path: str) -> str:
    return f"sqlite:///{path}"


settings = get_settings()
settings.ensure_runtime_dirs()
engine = create_engine(
    _sqlite_url(str(settings.business_db_path)),
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_business_db() -> None:
    settings.ensure_runtime_dirs()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
