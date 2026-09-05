from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_database_url() -> str:
    """Retrieve the database URL from environment or fallback to SQLite."""
    url = os.getenv("DATABASE_URL")
    if url:
        # Normalize postgres:// to postgresql:// for SQLAlchemy 2.x compatibility
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    data_dir = os.getenv("FINANCE_DATA_DIR")
    if data_dir:
        try:
            target_dir = os.path.abspath(data_dir)
            os.makedirs(target_dir, exist_ok=True)
            db_path = os.path.join(target_dir, "finance_controller.db")
            return f"sqlite:///{db_path.replace(os.sep, '/')}"
        except (PermissionError, OSError):
            pass
    return "sqlite:///./data/finance_controller.db"


def create_db_engine(database_url: str | None = None, echo: bool = False):
    """Create SQLAlchemy engine with appropriate dialect arguments."""
    url = database_url or get_database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        url,
        echo=echo,
        connect_args=connect_args,
        future=True,
    )


# Engine and sessionmaker singleton instances
engine = create_db_engine()
SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db(target_session_factory=None) -> Generator[Session, None, None]:
    """Dependency injector / context provider for DB session management."""
    factory = target_session_factory or SessionFactory
    db = factory()
    try:
        yield db
    finally:
        db.close()
