from decimal import Decimal

from app.models import TransactionRecord
from app.matching import match_records
from app.reporting import build_summary


def test_build_summary_for_reconciliation_results():
    payment = TransactionRecord("TX3001", "payment", Decimal("2500"), raw={"amount": "2500", "date": "2026-08-20"})
    bank = TransactionRecord("TX3001", "bank", Decimal("2500"), raw={"amount": "2500", "date": "2026-08-20"})
    ledger = TransactionRecord("TX3001", "ledger", Decimal("2500"), raw={"amount": "2500", "date": "2026-08-20"})

    mismatched_payment = TransactionRecord("TX3002", "payment", Decimal("5000"), raw={"amount": "5000", "date": "2026-08-20"})
    mismatched_bank = TransactionRecord("TX3002", "bank", Decimal("5000"), raw={"amount": "5000", "date": "2026-08-20"})
    mismatched_ledger = TransactionRecord("TX3002", "ledger", Decimal("4500"), raw={"amount": "4500", "date": "2026-08-20"})

    missing_payment = TransactionRecord("TX3003", "payment", Decimal("1500"), raw={"amount": "1500", "date": "2026-08-24"})
    missing_bank = TransactionRecord("TX3003", "bank", Decimal("1500"), raw={"amount": "1500", "date": "2026-08-24"})

    results = match_records(
        [payment, mismatched_payment, missing_payment],
        [bank, mismatched_bank, missing_bank],
        [ledger, mismatched_ledger],
    )

    summary = build_summary(results)

    assert summary["total_records"] == 3
    assert summary["matched"] == 1
    assert summary["unresolved"] == 2
    assert summary["match_rate"] == 33.33
    assert summary["exception_breakdown"]["amount_mismatch"] == 1
    assert summary["exception_breakdown"]["missing_ledger"] == 1
