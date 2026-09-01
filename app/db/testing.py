"""Test-only database helpers.

This module must NEVER be imported by application code.
It exists solely to support isolated pytest fixtures that need
to create a fresh schema without running Alembic.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

from app.db.session import Base
import app.db.models  # noqa: F401 — registers all ORM models with Base.metadata


def create_all_tables(engine: Engine) -> None:
    """Create all tables directly via SQLAlchemy metadata.

    Use ONLY in test fixtures against a temporary/in-memory database.
    Never call this against a production or shared database.
    """
    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine: Engine) -> None:
    """Drop all tables. Use ONLY in test teardown."""
    Base.metadata.drop_all(bind=engine)
