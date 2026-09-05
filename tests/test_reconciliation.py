from decimal import Decimal

from app.models import TransactionRecord
from app.matching import match_records
from app.normalization import normalize_records


def test_clean_match():
    records = [
        TransactionRecord("TX1001", "payment", Decimal("2500"), raw={"amount": "2500", "date": "2026-08-20"}),
        TransactionRecord("TX1001", "bank", Decimal("2500"), raw={"amount": "2500", "date": "2026-08-20"}),
        TransactionRecord("TX1001", "ledger", Decimal("2500"), raw={"amount": "2500", "date": "2026-08-20"}),
    ]
    result = match_records(records[0:1], records[1:2], records[2:3])
    assert result[0].matched is True
    assert result[0].exception_type is None


def test_amount_mismatch():
    payment = TransactionRecord("TX1002", "payment", Decimal("5000"), raw={"amount": "5000", "date": "2026-08-20"})
    bank = TransactionRecord("TX1002", "bank", Decimal("5000"), raw={"amount": "5000", "date": "2026-08-20"})
    ledger = TransactionRecord("TX1002", "ledger", Decimal("4500"), raw={"amount": "4500", "date": "2026-08-20"})
    result = match_records([payment], [bank], [ledger])
    assert result[0].matched is False
    assert result[0].exception_type == "amount_mismatch"


def test_missing_ledger():
    payment = TransactionRecord("TX1006", "payment", Decimal("1500"), raw={"amount": "1500", "date": "2026-08-24"})
    bank = TransactionRecord("TX1006", "bank", Decimal("1500"), raw={"amount": "1500", "date": "2026-08-24"})
    result = match_records([payment], [bank], [])
    assert result[0].exception_type == "missing_ledger"


def test_normalize_finance_record_fields():
    record = TransactionRecord(
        "TX2001",
        "payment",
        Decimal("0"),
        raw={
            "amount": "₹2,500",
            "date": "20-Aug-2026",
            "status": "success",
            "reference_id": "REF2001",
            "customer_id": "CUST2001",
            "order_id": "ORD2001",
        },
    )

    normalized = normalize_records([record])[0]

    assert normalized.amount == Decimal("2500")
    assert normalized.transaction_date.isoformat() == "2026-08-20"
    assert normalized.status == "SETTLED"
    assert normalized.reference_id == "REF2001"
    assert normalized.customer_id == "CUST2001"
    assert normalized.order_id == "ORD2001"


def test_status_mismatch():
    payment = TransactionRecord("TX2002", "payment", Decimal("5000"), status="SUCCESS", raw={"amount": "5000", "date": "2026-08-20", "status": "SUCCESS"})
    bank = TransactionRecord("TX2002", "bank", Decimal("5000"), status="POSTED", raw={"amount": "5000", "date": "2026-08-20", "status": "POSTED"})
    ledger = TransactionRecord("TX2002", "ledger", Decimal("5000"), status="FAILED", raw={"amount": "5000", "date": "2026-08-20", "status": "FAILED"})

    result = match_records([payment], [bank], [ledger])[0]

    assert result.matched is False
    assert result.exception_type == "status_mismatch"


def test_date_mismatch():
    payment = TransactionRecord("TX2003", "payment", Decimal("1000"), status="SUCCESS", raw={"amount": "1000", "date": "2026-08-20", "status": "SUCCESS"})
    bank = TransactionRecord("TX2003", "bank", Decimal("1000"), status="POSTED", raw={"amount": "1000", "date": "2026-08-21", "status": "POSTED"})
    ledger = TransactionRecord("TX2003", "ledger", Decimal("1000"), status="PAID", raw={"amount": "1000", "date": "2026-08-20", "status": "PAID"})

    result = match_records([payment], [bank], [ledger])[0]

    assert result.matched is False
    assert result.exception_type == "date_mismatch"
