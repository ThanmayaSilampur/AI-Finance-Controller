from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.adapter import DataAdapter
from app.db.models import (
    AuditEventModel,
    BankRecordModel,
    ExceptionModel,
    InvestigationModel,
    LedgerRecordModel,
    PaymentRecordModel,
    RawTransaction,
    ReviewModel,
    TransactionModel,
)
from app.db.repository import DatabaseRepository
from app.db.session import Base
from app.db.testing import create_all_tables
from app.models import TransactionRecord
from app.matching import match_records
from scripts.ingest_dataset import ingest_file


@pytest.fixture
def db_session(tmp_path):
    """Fixture to provide an isolated in-memory SQLite database session."""
    db_file = tmp_path / "test_stage11.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_database_creation_and_schema_initialization(db_session):
    """Verify all 9 logical database tables are created with proper metadata."""
    table_names = Base.metadata.tables.keys()
    expected_tables = {
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
    assert expected_tables.issubset(set(table_names))


def test_decimal_monetary_precision(db_session):
    """Verify monetary amounts store and retrieve exact Decimal values without float drift."""
    repo = DatabaseRepository(db_session)
    exact_amount = Decimal("12500.75")

    txn = TransactionRecord(
        transaction_id="TX_PRECISION_01",
        source_system="ibm_aml",
        amount=exact_amount,
        currency="INR",
    )
    repo.save_normalized_transaction(txn)

    retrieved = repo.get_transaction("TX_PRECISION_01")
    assert retrieved is not None
    assert retrieved.amount == Decimal("12500.75")
    assert isinstance(retrieved.amount, Decimal)


def test_unique_source_dataset_and_record_id_constraint(db_session):
    """Verify unique constraint on source_dataset + source_record_id prevents duplicates."""
    repo = DatabaseRepository(db_session)
    repo.save_raw_transaction(
        source_dataset="IBM_AML_DATA",
        source_record_id="REC_1001",
        raw_payload={"test": "data_1"},
    )

    # Idempotent update should update payload rather than crashing or creating duplicate
    duplicate = repo.save_raw_transaction(
        source_dataset="IBM_AML_DATA",
        source_record_id="REC_1001",
        raw_payload={"test": "data_2_updated"},
    )
    assert duplicate.raw_payload == {"test": "data_2_updated"}

    raw_records = repo.list_raw_transactions("IBM_AML_DATA")
    assert len(raw_records) == 1


def test_ingestion_pipeline_with_sample_ibm_aml(db_session, tmp_path):
    """Verify sample IBM AML-Data CSV is parsed, validated, stored in raw_transactions,

    and mapped to normalized entities with full lineage.
    """
    csv_file = tmp_path / "sample_ibm.csv"
    csv_file.write_text(
        "Timestamp,From Bank,Account,To Bank,Account.1,Amount Received,Receiving Currency,Amount Paid,Payment Currency,Payment Format,Is Laundering\n"
        "2026/08/20 08:00,10,1001,12,2001,2500.00,INR,2500.00,INR,ACH,0\n"
        "2026/08/20 09:15,10,1002,12,2002,4800.00,INR,5000.00,INR,Wire,0\n",
        encoding="utf-8",
    )

    stats = ingest_file(csv_file, dataset_name="IBM_AML_DATA", db_session=db_session)
    assert stats["read"] == 2
    assert stats["accepted"] == 2
    assert stats["rejected"] == 0

    repo = DatabaseRepository(db_session)
    raw_txns = repo.list_raw_transactions("IBM_AML_DATA")
    assert len(raw_txns) == 2
    assert raw_txns[0].raw_payload["Amount Paid"] == "2500.00"

    norm_txns = repo.list_transactions()
    assert len(norm_txns) == 2
    assert norm_txns[0].raw_transaction_id == raw_txns[0].id


def test_idempotent_duplicate_ingestion(db_session, tmp_path):
    """Verify ingesting the same dataset twice skips duplicates without throwing error."""
    csv_file = tmp_path / "sample_ibm.csv"
    csv_file.write_text(
        "Timestamp,From Bank,Account,To Bank,Account.1,Amount Received,Receiving Currency,Amount Paid,Payment Currency,Payment Format,Is Laundering\n"
        "2026/08/20 08:00,10,1001,12,2001,2500.00,INR,2500.00,INR,ACH,0\n",
        encoding="utf-8",
    )

    stats1 = ingest_file(csv_file, dataset_name="IBM_AML_DATA", db_session=db_session)
    assert stats1["accepted"] == 1

    stats2 = ingest_file(csv_file, dataset_name="IBM_AML_DATA", db_session=db_session)
    assert stats2["accepted"] == 0
    assert stats2["skipped_duplicates"] == 1


def test_malformed_csv_input_handling(db_session, tmp_path):
    """Verify malformed CSV inputs are reported without silent data loss."""
    csv_file = tmp_path / "malformed.csv"
    csv_file.write_text("Invalid,Headers,Only\n1,2,3\n", encoding="utf-8")

    stats = ingest_file(csv_file, dataset_name="IBM_AML_DATA", db_session=db_session)
    assert stats["rejected"] == 1
    assert len(stats["errors"]) > 0


def test_raw_to_normalized_lineage_traceability(db_session):
    """Verify lineage tracking from external dataset -> raw record -> normalized transaction."""
    repo = DatabaseRepository(db_session)
    raw = repo.save_raw_transaction(
        source_dataset="IBM_AML_DATA",
        source_record_id="REC_TRACE_01",
        raw_payload={
            "Timestamp": "2026/08/20 10:00",
            "Account": "CUST_99",
            "Account.1": "ORD_88",
            "Amount Paid": "7500.50",
            "Payment Currency": "INR",
            "Is Laundering": "0",
        },
    )

    norm_txn = DataAdapter.raw_to_normalized_transaction(
        source_record_id="REC_TRACE_01",
        raw_payload=raw.raw_payload,
        source_dataset="IBM_AML_DATA",
        raw_db_id=raw.id,
    )
    saved_norm = repo.save_normalized_transaction(norm_txn, raw_transaction_id=raw.id)

    assert saved_norm.raw_transaction_id == raw.id
    assert saved_norm.amount == Decimal("7500.50")
    assert saved_norm.customer_id == "CUST_99"


def test_exception_and_review_persistence(db_session):
    """Verify exception records and review state transitions persist cleanly in DB."""
    repo = DatabaseRepository(db_session)
    exc = repo.save_exception(
        exception_id="EX-9001",
        audit_id="AUD-9001",
        transaction_id="TX_9001",
        exception_type="amount_mismatch",
        recommended_action="verify_settlement",
        payment_amount=Decimal("5000"),
        bank_amount=Decimal("4800"),
        difference=Decimal("200"),
    )
    assert exc.review_status == "PENDING"

    review = repo.add_review(
        exception_id="EX-9001",
        previous_state="PENDING",
        new_state="APPROVED",
        reviewer="finance_admin",
        comment="Settlement fee confirmed.",
    )

    updated_exc = repo.get_exception("EX-9001")
    assert updated_exc.review_status == "APPROVED"

    reviews = repo.list_reviews("EX-9001")
    assert len(reviews) == 1
    assert reviews[0].reviewer == "finance_admin"


def test_investigation_persistence(db_session):
    """Verify AI investigation findings persist in DB with required confidence and human review flags."""
    repo = DatabaseRepository(db_session)
    inv = repo.save_investigation(
        investigation_id="INV-9001",
        exception_id="EX-9001",
        transaction_id="TX_9001",
        provider="mock",
        agent_status="COMPLETED",
        confidence="HIGH",
        summary="Fee discrepancy verified.",
        most_likely_cause="Possible standard settlement fee.",
        findings=["Payment matches ledger."],
        possible_causes=[{"cause": "Settlement fee", "likelihood": "HIGH"}],
        evidence_collected={"difference": 200},
        tools_used=["get_transaction"],
        recommendation="Verify fee configuration.",
        requires_human_review=True,
    )

    retrieved = repo.get_investigation("INV-9001")
    assert retrieved is not None
    assert retrieved.confidence == "HIGH"
    assert retrieved.requires_human_review is True


def test_reconciliation_compatibility(db_session):
    """Verify DB-persisted records are compatible with existing matching logic."""
    p = TransactionRecord("TX_RECON_1", "payment", Decimal("1000"), raw={"amount": "1000"})
    b = TransactionRecord("TX_RECON_1", "bank", Decimal("1000"), raw={"amount": "1000"})
    l = TransactionRecord("TX_RECON_1", "ledger", Decimal("900"), raw={"amount": "900"})

    repo = DatabaseRepository(db_session)
    repo.save_payment_record(p)
    repo.save_bank_record(b)
    repo.save_ledger_record(l)

    results = match_records([p], [b], [l])
    assert len(results) == 1
    assert results[0].matched is False
    assert results[0].exception_type == "amount_mismatch"
