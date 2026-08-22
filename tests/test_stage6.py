from decimal import Decimal

import pytest

from app.audit import (
    AuditStore,
    ReviewState,
    approve_exception,
    build_exception_explanation,
    detect_duplicate_transaction,
    detect_fee_difference,
    escalate_exception,
    get_exception_details,
    list_pending_exceptions,
    reject_exception,
    transition_review_state,
)
from app.matching import match_records
from app.models import TransactionRecord
from app.reporting import build_exception_report, export_exception_report


def test_audit_record_creation_and_storage(tmp_path):
    store = AuditStore(str(tmp_path / "audit.json"))
    record = store.create_record(
        transaction_id="TX5001",
        match_status="EXCEPTION",
        exception_type="AMOUNT_MISMATCH",
        payment_amount=5000,
        bank_amount=4800,
        ledger_amount=5000,
        difference=200,
        recommended_action="VERIFY_SETTLEMENT_DIFFERENCE",
    )

    assert record["review_status"] == "PENDING"
    assert record["audit_id"].startswith("AUD-")
    assert store.get_record(record["audit_id"])["transaction_id"] == "TX5001"


def test_pending_initial_state_and_approved_transition(tmp_path):
    store = AuditStore(str(tmp_path / "audit.json"))
    record = store.create_record(transaction_id="TX5002", match_status="EXCEPTION", exception_type="AMOUNT_MISMATCH")

    approved = transition_review_state(store, record["audit_id"], ReviewState.APPROVED, "finance_admin", "Confirmed fee difference.")

    assert approved["review_status"] == "APPROVED"
    assert approved["review_history"][-1]["reviewer"] == "finance_admin"


def test_invalid_transition_rejected(tmp_path):
    store = AuditStore(str(tmp_path / "audit.json"))
    record = store.create_record(transaction_id="TX5003", match_status="EXCEPTION", exception_type="AMOUNT_MISMATCH")

    approved = transition_review_state(store, record["audit_id"], ReviewState.APPROVED, "finance_admin", "ok")
    with pytest.raises(ValueError):
        transition_review_state(store, record["audit_id"], ReviewState.PENDING, "other", "illegal")

    assert approved["review_status"] == "APPROVED"


def test_duplicate_detection():
    payment = TransactionRecord("TX5004", "payment", Decimal("1000"), raw={"amount": "1000", "date": "2026-08-20"})
    bank = TransactionRecord("TX5004", "bank", Decimal("1000"), raw={"amount": "1000", "date": "2026-08-20"})
    duplicate = TransactionRecord("TX5004", "ledger", Decimal("1000"), raw={"amount": "1000", "date": "2026-08-20"})

    assert detect_duplicate_transaction([payment, duplicate]) is True


def test_fee_difference_detection():
    payment = Decimal("1000")
    settlement = Decimal("980")

    assert detect_fee_difference(payment, settlement) is True


def test_exception_explanation_generation():
    explanation = build_exception_explanation(
        expected="₹5,000",
        observed="₹4,800",
        difference="₹200",
        evidence="Payment and ledger show ₹5,000 while bank settlement shows ₹4,800.",
        likely_reason="Possible settlement fee.",
        recommended_action="Verify settlement fee configuration.",
    )

    assert explanation["likely_reason"] == "Possible settlement fee."
    assert explanation["recommended_action"] == "Verify settlement fee configuration."


def test_batch_report_calculations():
    payment = TransactionRecord("TX5005", "payment", Decimal("2500"), raw={"amount": "2500", "date": "2026-08-20"})
    bank = TransactionRecord("TX5005", "bank", Decimal("2500"), raw={"amount": "2500", "date": "2026-08-20"})
    ledger = TransactionRecord("TX5005", "ledger", Decimal("2500"), raw={"amount": "2500", "date": "2026-08-20"})

    bad_payment = TransactionRecord("TX5006", "payment", Decimal("5000"), raw={"amount": "5000", "date": "2026-08-20"})
    bad_bank = TransactionRecord("TX5006", "bank", Decimal("5000"), raw={"amount": "5000", "date": "2026-08-20"})
    bad_ledger = TransactionRecord("TX5006", "ledger", Decimal("4500"), raw={"amount": "4500", "date": "2026-08-20"})

    results = match_records([payment, bad_payment], [bank, bad_bank], [ledger, bad_ledger])
    report = build_exception_report(results)

    assert report["total_records"] == 2
    assert report["matched_records"] == 1
    assert report["exception_count"] == 1
    assert report["match_rate"] == 50.0
    assert report["exception_breakdown"]["amount_mismatch"] == 1


def test_export_generation(tmp_path):
    payment = TransactionRecord("TX5007", "payment", Decimal("2000"), raw={"amount": "2000", "date": "2026-08-20"})
    bank = TransactionRecord("TX5007", "bank", Decimal("1800"), raw={"amount": "1800", "date": "2026-08-20"})
    ledger = TransactionRecord("TX5007", "ledger", Decimal("2000"), raw={"amount": "2000", "date": "2026-08-20"})

    results = match_records([payment], [bank], [ledger])
    export_path = tmp_path / "exceptions.json"

    export_exception_report(results, str(export_path), fmt="json")

    assert export_path.exists()
    data = export_path.read_text(encoding="utf-8")
    assert "TX5007" in data
    assert "amount_mismatch" in data


def test_review_function_helpers(tmp_path):
    store = AuditStore(str(tmp_path / "audit.json"))
    approved_record = store.create_record(transaction_id="TX5008", match_status="EXCEPTION", exception_type="AMOUNT_MISMATCH")
    rejected_record = store.create_record(transaction_id="TX5009", match_status="EXCEPTION", exception_type="MISSING_RECORD")

    pending = list_pending_exceptions(store)
    assert len(pending) == 2

    approved = approve_exception(store, approved_record["audit_id"], "finance_admin", "Approved after checking ledger.")
    assert approved["review_status"] == "APPROVED"

    details = get_exception_details(store, approved_record["audit_id"])
    assert details["review_status"] == "APPROVED"

    escalated = escalate_exception(store, approved_record["audit_id"], "finance_admin", "Escalated for second review.")
    assert escalated["review_status"] == "ESCALATED"

    rejected = reject_exception(store, rejected_record["audit_id"], "finance_admin", "Not enough evidence.")
    assert rejected["review_status"] == "REJECTED"
