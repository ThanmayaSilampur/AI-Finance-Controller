"""Programmatic Alembic migration runner.

Called by FinanceService on startup to ensure the schema is at head
before the application begins serving requests.  This replaces the
former Base.metadata.create_all() call and makes Alembic the single
authoritative schema lifecycle mechanism.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"


def run_migrations(database_url: str) -> None:
    """Run ``alembic upgrade head`` against *database_url*.

    Safe to call on every startup:
    - If the database is already at head, Alembic is a no-op.
    - If the database is fresh, Alembic creates the full schema.
    - If the database is behind head, Alembic applies pending migrations.
    """
    cfg = AlembicConfig(str(_ALEMBIC_INI))
    # Resolve script_location to an absolute path so this works regardless
    # of the process working directory (e.g. when called from tests).
    cfg.set_main_option("script_location", str(_ALEMBIC_INI.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    alembic_command.upgrade(cfg, "head")
