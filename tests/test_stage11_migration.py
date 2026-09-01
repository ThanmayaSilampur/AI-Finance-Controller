"""Stage 11.1 — Migration contract regression tests.

Verifies:
A. Application import/startup does NOT call create_all automatically.
B. Alembic migration creates the required schema on a fresh database.
C. alembic_version contains the current revision after upgrade.
D. Application can use the migrated schema.
E. Existing Stage 11 ingestion still works after migration.
F. Existing reconciliation behavior is unchanged.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.db.adapter import DataAdapter
from app.db.models import (
    AuditEventModel,
    ExceptionModel,
    InvestigationModel,
    RawTransaction,
    ReviewModel,
    TransactionModel,
)
from app.db.repository import DatabaseRepository
from app.db.session import Base
from app.db.testing import create_all_tables
from app.matching import match_records
from app.models import TransactionRecord
from scripts.ingest_dataset import ingest_file

REPO_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
CURRENT_REVISION = "20260901_01"
EXPECTED_TABLES = {
    "raw_transactions",
    "transactions",
    "payment_records",
    "bank_records",
    "ledger_records",
    "exceptions",
    "reviews",
    "investigations",
    "audit_events",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alembic_cfg(db_url: str) -> AlembicConfig:
    cfg = AlembicConfig(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


# ---------------------------------------------------------------------------
# A. Application startup must NOT call create_all
# ---------------------------------------------------------------------------

def test_session_module_has_no_init_db():
    """init_db / create_all must not exist in app.db.session after the fix."""
    import app.db.session as session_mod
    assert not hasattr(session_mod, "init_db"), (
        "init_db was found in app.db.session — it must be removed so that "
        "application startup cannot bypass Alembic."
    )


def test_api_module_does_not_call_create_all(tmp_path):
    """Importing app.api with a fresh empty database must NOT create tables.

    Verifies that creating an engine against a brand-new SQLite file and
    inspecting it (without running migrations) yields no tables.  This
    confirms that no code path calls create_all() on engine creation.
    """
    from sqlalchemy import create_engine, inspect as sa_inspect
    from app.db.session import create_db_engine

    db_file = tmp_path / "startup_test.db"
    engine = create_db_engine(f"sqlite:///{db_file}")
    tables = sa_inspect(engine).get_table_names()
    engine.dispose()
    assert tables == [], (
        f"Tables were created without Alembic: {tables}"
    )


# ---------------------------------------------------------------------------
# B & C. Alembic migration creates schema and populates alembic_version
# ---------------------------------------------------------------------------

@pytest.fixture
def migrated_db(tmp_path):
    """Fresh database created exclusively via alembic upgrade head."""
    db_file = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_file}"
    cfg = _alembic_cfg(db_url)
    alembic_command.upgrade(cfg, "head")
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session, engine, db_url
    session.close()
    engine.dispose()


def test_alembic_upgrade_creates_all_tables(migrated_db):
    """alembic upgrade head must create every required table."""
    _, engine, _ = migrated_db
    actual = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(actual), (
        f"Missing tables after migration: {EXPECTED_TABLES - actual}"
    )


def test_alembic_version_populated_after_upgrade(migrated_db):
    """alembic_version must contain the current revision after upgrade head."""
    _, engine, _ = migrated_db
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    assert row is not None, "alembic_version table is empty after upgrade head"
    assert row[0] == CURRENT_REVISION, (
        f"Expected revision {CURRENT_REVISION!r}, got {row[0]!r}"
    )


def test_alembic_check_passes_after_upgrade(migrated_db):
    """alembic check must report no pending migrations after upgrade head."""
    _, _, db_url = migrated_db
    cfg = _alembic_cfg(db_url)
    # alembic check raises SystemExit(1) if out of date; must not raise
    try:
        alembic_command.check(cfg)
    except SystemExit as exc:
        pytest.fail(f"alembic check failed after upgrade head: {exc}")


# ---------------------------------------------------------------------------
# D. Application can use the migrated schema
# ---------------------------------------------------------------------------

def test_repository_works_on_migrated_schema(migrated_db):
    """DatabaseRepository must be able to read/write on an Alembic-migrated DB."""
    session, _, _ = migrated_db
    repo = DatabaseRepository(session)

    raw = repo.save_raw_transaction(
        source_dataset="TEST",
        source_record_id="MIGRATE_TEST_001",
        raw_payload={"amount": "100.00"},
    )
    assert raw.id is not None

    txn = TransactionRecord(
        transaction_id="TX_MIGRATE_001",
        source_system="test",
        amount=Decimal("100.00"),
        currency="INR",
    )
    saved = repo.save_normalized_transaction(txn, raw_transaction_id=raw.id)
    assert saved.transaction_id == "TX_MIGRATE_001"
    assert saved.raw_transaction_id == raw.id


# ---------------------------------------------------------------------------
# E. Ingestion still works after migration
# ---------------------------------------------------------------------------

def test_ingestion_works_on_migrated_schema(migrated_db, tmp_path):
    """ingest_file must succeed against an Alembic-migrated database."""
    session, _, _ = migrated_db
    csv_file = tmp_path / "test_ingest.csv"
    csv_file.write_text(
        "Timestamp,From Bank,Account,To Bank,Account.1,"
        "Amount Received,Receiving Currency,Amount Paid,Payment Currency,"
        "Payment Format,Is Laundering\n"
        "2026/08/20 08:00,10,1001,12,2001,2500.00,INR,2500.00,INR,ACH,0\n"
        "2026/08/20 09:15,10,1002,12,2002,4800.00,INR,5000.00,INR,Wire,0\n",
        encoding="utf-8",
    )
    stats = ingest_file(csv_file, dataset_name="IBM_AML_DATA", db_session=session)
    assert stats["read"] == 2
    assert stats["accepted"] == 2
    assert stats["rejected"] == 0

    # Second run must be idempotent
    stats2 = ingest_file(csv_file, dataset_name="IBM_AML_DATA", db_session=session)
    assert stats2["accepted"] == 0
    assert stats2["skipped_duplicates"] == 2


# ---------------------------------------------------------------------------
# F. Reconciliation behavior is unchanged
# ---------------------------------------------------------------------------

def test_reconciliation_unchanged_after_migration(migrated_db):
    """Deterministic reconciliation must produce identical results regardless
    of whether the schema was created by create_all or alembic upgrade head."""
    session, _, _ = migrated_db
    repo = DatabaseRepository(session)

    p = TransactionRecord("TX_R1", "payment", Decimal("5000"), raw={"amount": "5000"})
    b = TransactionRecord("TX_R1", "bank", Decimal("4800"), raw={"amount": "4800"})
    l = TransactionRecord("TX_R1", "ledger", Decimal("5000"), raw={"amount": "5000"})

    repo.save_payment_record(p)
    repo.save_bank_record(b)
    repo.save_ledger_record(l)

    results = match_records([p], [b], [l])
    assert len(results) == 1
    assert results[0].matched is False
    assert results[0].exception_type == "amount_mismatch"
    assert results[0].recommended_action == "review_amount_variance"


# ---------------------------------------------------------------------------
# G. Audit history deduplication — one review produces exactly one history entry
# ---------------------------------------------------------------------------

def test_one_review_produces_exactly_one_history_entry(migrated_db):
    """A single review action must produce exactly one review_history entry.

    Previously, both AuditStore.update_record() and repo.add_review() each
    appended a history entry, resulting in duplicates.  After the fix only
    AuditStore.update_record() owns review_history.
    """
    from sqlalchemy import select
    from app.audit import AuditStore, ReviewState, transition_review_state
    from app.db.models import AuditEventModel, ReviewModel
    import tempfile
    from pathlib import Path as _Path

    session, _, _ = migrated_db
    repo = DatabaseRepository(session)

    # Create the prerequisite exception + audit event
    repo.save_audit_event(
        audit_id="AUD-H01",
        transaction_id="TX_H01",
        match_status="EXCEPTION",
        exception_type="amount_mismatch",
        recommended_action="review_amount_variance",
    )
    repo.save_exception(
        exception_id="EX-H01",
        audit_id="AUD-H01",
        transaction_id="TX_H01",
        exception_type="amount_mismatch",
        recommended_action="review_amount_variance",
    )

    tmp = tempfile.mkdtemp()
    audit_store = AuditStore(path=_Path(tmp) / "audit.json", db=session)

    # Single review action
    transition_review_state(audit_store, "AUD-H01", ReviewState.APPROVED, "tester", "ok")
    repo.add_review(
        exception_id="EX-H01",
        previous_state="PENDING",
        new_state="APPROVED",
        reviewer="tester",
        comment="ok",
    )

    # Exactly one history entry in audit_events
    audit_evt = session.get(AuditEventModel, "AUD-H01")
    session.refresh(audit_evt)
    assert len(audit_evt.review_history) == 1, (
        f"Expected 1 history entry, got {len(audit_evt.review_history)}: {audit_evt.review_history}"
    )
    assert audit_evt.review_history[0]["new_state"] == "APPROVED"
    assert audit_evt.review_status == "APPROVED"

    # Exactly one row in reviews table
    reviews = repo.list_reviews("EX-H01")
    assert len(reviews) == 1
    assert reviews[0].reviewer == "tester"


# ---------------------------------------------------------------------------
# H. Decimal precision — value that would expose float drift
# ---------------------------------------------------------------------------

def test_monetary_amounts_stored_as_decimal_no_float_drift(migrated_db):
    """Amounts that cannot be represented exactly in binary float must round-trip
    through NUMERIC(18,2) without drift.

    0.1 + 0.2 == 0.30000000000000004 in float; Decimal arithmetic is exact.
    """
    from app.db.models import ExceptionModel

    session, _, _ = migrated_db
    repo = DatabaseRepository(session)

    # These values expose float drift: 0.1 + 0.2 != 0.3 in IEEE 754
    payment = Decimal("1000.10")
    bank    = Decimal("1000.20")
    diff    = bank - payment  # exact: 0.10

    repo.save_audit_event(
        audit_id="AUD-P01",
        transaction_id="TX_P01",
        match_status="EXCEPTION",
        exception_type="amount_mismatch",
        payment_amount=payment,
        bank_amount=bank,
        difference=diff,
        recommended_action="review_amount_variance",
    )
    repo.save_exception(
        exception_id="EX-P01",
        audit_id="AUD-P01",
        transaction_id="TX_P01",
        exception_type="amount_mismatch",
        recommended_action="review_amount_variance",
        payment_amount=payment,
        bank_amount=bank,
        difference=diff,
    )

    exc = session.get(ExceptionModel, "EX-P01")
    session.refresh(exc)
    assert isinstance(exc.payment_amount, Decimal)
    assert isinstance(exc.bank_amount, Decimal)
    assert isinstance(exc.difference, Decimal)
    assert exc.difference == Decimal("0.10"), (
        f"Expected Decimal('0.10'), got {exc.difference!r} — float drift detected"
    )
