from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List

from app.models import TransactionRecord


def load_records(file_path: str | Path, source_system: str) -> List[TransactionRecord]:
    """Load records from a CSV file into TransactionRecord objects."""
    records: List[TransactionRecord] = []
    path = Path(file_path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            record = TransactionRecord(
                transaction_id=str(row.get("transaction_id") or row.get("id") or "UNKNOWN"),
                source_system=source_system,
                amount=0,
                currency=str(row.get("currency") or "INR"),
                transaction_date=None,
                status=str(row.get("status") or "UNKNOWN"),
                reference_id=str(row.get("reference_id") or row.get("reference") or row.get("transaction_id") or "UNKNOWN"),
                customer_id=str(row.get("customer_id") or row.get("customer") or "").strip() or None,
                order_id=str(row.get("order_id") or row.get("order") or "").strip() or None,
                raw=dict(row),
            )
            records.append(record)

    return records
