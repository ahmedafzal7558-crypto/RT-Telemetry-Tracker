"""
SQLAlchemy database engine and session management.

Provides a shared engine, a session factory, and a FastAPI dependency that
yields per-request sessions that are automatically closed.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from app.core.config import get_settings

settings = get_settings()

# Allow the DATABASE_URL to be overridden by a direct env var at runtime
# (useful in Docker / CI where the URL may be injected differently).
_DATABASE_URL: str = os.getenv(
    "DATABASE_URL", settings.DATABASE_URL
)

engine: Engine = create_engine(
    _DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

SessionLocal: sessionmaker = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and closes it on exit."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
