from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable, List, Sequence

from app.models import TransactionRecord


def normalize_amount(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    text = str(value).strip()
    text = text.replace("INR", "").replace("₹", "").replace(",", "").replace(" ", "")
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def normalize_date(value: object):
    if value is None or value == "":
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%b", "%d-%b-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalize_status(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    text = str(value).strip().upper()
    return text if text else "UNKNOWN"


def normalize_records(records: Sequence[TransactionRecord]) -> List[TransactionRecord]:
    normalized: List[TransactionRecord] = []
    for record in records:
        raw = dict(record.raw)
        normalized_record = TransactionRecord(
            transaction_id=str(record.transaction_id),
            source_system=record.source_system,
            amount=normalize_amount(raw.get("amount") or raw.get("value") or record.amount),
            currency=str(raw.get("currency") or record.currency or "INR").upper(),
            transaction_date=normalize_date(raw.get("transaction_date") or raw.get("date") or record.transaction_date),
            status=normalize_status(raw.get("status") or record.status),
            reference_id=str(record.reference_id or raw.get("reference_id") or raw.get("reference") or record.transaction_id),
            customer_id=str(raw.get("customer_id") or raw.get("customer") or record.customer_id or "").strip() or None,
            order_id=str(raw.get("order_id") or raw.get("order") or record.order_id or "").strip() or None,
            raw=raw,
        )
        normalized.append(normalized_record)
    return normalized
