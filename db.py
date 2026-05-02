import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base

_engine = None
_session_maker = None


def _normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _configure() -> None:
    global _engine, _session_maker
    if _engine is not None:
        return
    raw = os.environ.get("DATABASE_URL", "")
    url = _normalize_url(raw.strip())
    if not url:
        raise RuntimeError("DATABASE_URL no está definida")
    _engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _session_maker = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def init_db() -> None:
    _configure()
    assert _engine is not None
    Base.metadata.create_all(bind=_engine)


def SessionLocal() -> Session:
    _configure()
    assert _session_maker is not None
    return _session_maker()
