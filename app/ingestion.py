from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import List, Optional

from app.models import TransactionRecord
from app.normalization import normalize_amount, normalize_date, normalize_status

# ---------------------------------------------------------------------------
# Column alias mappings — order matters: first match wins
# ---------------------------------------------------------------------------
_ID_ALIASES = [
    "transaction_id", "txn_id", "tx_id", "transaction", "id",
    "reference_id", "reference",
]
_AMOUNT_ALIASES = [
    "amount", "transaction_amount", "value", "amount_paid",
    "amount_received", "net_amount",
]
_CURRENCY_ALIASES = ["currency", "curr", "payment_currency", "receiving_currency"]
_DATE_ALIASES = ["date", "transaction_date", "timestamp", "posted_date", "value_date"]
_STATUS_ALIASES = ["status", "payment_status", "state", "record_status"]
_CUSTOMER_ALIASES = ["customer_id", "customer", "cust_id", "account", "from_account"]
_ORDER_ALIASES = ["order_id", "order", "to_account", "account.1"]


def _find_col(fieldnames: List[str], aliases: List[str]) -> Optional[str]:
    """Return the first column name (case-insensitive) that matches an alias."""
    lower_fields = {f.strip().lower(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower() in lower_fields:
            return lower_fields[alias.lower()]
    return None


def parse_csv_records(
    file_content: str | bytes,
    source_system: str,
    filename: str = "<upload>",
) -> List[TransactionRecord]:
    """Parse CSV bytes/text into TransactionRecord objects with flexible column mapping.

    Raises:
        ValueError: If mandatory columns (transaction_id, amount) cannot be resolved.
    """
    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8-sig")  # strip BOM if present

    reader = csv.DictReader(io.StringIO(file_content))
    if reader.fieldnames is None:
        return []

    fields: List[str] = list(reader.fieldnames)

    id_col = _find_col(fields, _ID_ALIASES)
    if id_col is None:
        raise ValueError(
            f"Unable to identify transaction ID column in {filename}. "
            f"Found columns: {fields}"
        )

    amount_col = _find_col(fields, _AMOUNT_ALIASES)
    if amount_col is None:
        raise ValueError(
            f"Unable to identify amount column in {filename}. "
            f"Found columns: {fields}"
        )

    currency_col = _find_col(fields, _CURRENCY_ALIASES)
    date_col = _find_col(fields, _DATE_ALIASES)
    status_col = _find_col(fields, _STATUS_ALIASES)
    customer_col = _find_col(fields, _CUSTOMER_ALIASES)
    order_col = _find_col(fields, _ORDER_ALIASES)

    records: List[TransactionRecord] = []
    for row in reader:
        txn_id = str(row.get(id_col) or "UNKNOWN").strip()
        raw = dict(row)

        record = TransactionRecord(
            transaction_id=txn_id,
            source_system=source_system,
            amount=normalize_amount(row.get(amount_col)),
            currency=str(row.get(currency_col) or "INR").strip().upper() if currency_col else "INR",
            transaction_date=normalize_date(row.get(date_col)) if date_col else None,
            status=normalize_status(row.get(status_col)) if status_col else "UNKNOWN",
            reference_id=str(row.get(id_col) or txn_id).strip(),
            customer_id=str(row.get(customer_col) or "").strip() or None if customer_col else None,
            order_id=str(row.get(order_col) or "").strip() or None if order_col else None,
            raw=raw,
        )
        records.append(record)

    return records


def load_records(file_path: str | Path, source_system: str) -> List[TransactionRecord]:
    """Load records from a CSV file into TransactionRecord objects."""
    path = Path(file_path)
    content = path.read_bytes()
    return parse_csv_records(content, source_system, filename=str(path.name))
