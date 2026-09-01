from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from app.models import TransactionRecord
from app.normalization import normalize_amount, normalize_date, normalize_status


class DataAdapter:
    """Adapter for translating external datasets (e.g., IBM AML-Data) into raw records,

    normalized domain models, and reconciliation input streams.
    """

    @staticmethod
    def extract_source_record_id(row: Dict[str, Any], record_index: int) -> str:
        """Derive a deterministic source record identifier from raw data row."""
        # Look for explicit ID or synthesize from timestamp + accounts + index
        if row.get("source_record_id"):
            return str(row["source_record_id"])
        if row.get("id"):
            return str(row["id"])

        ts = str(row.get("Timestamp") or row.get("timestamp") or "").strip()
        from_acc = str(row.get("Account") or row.get("from_account") or "").strip()
        to_acc = str(row.get("Account.1") or row.get("To Account") or row.get("to_account") or "").strip()

        if ts and from_acc:
            return f"IBM-{ts.replace(' ', 'T').replace('/', '-')}-{from_acc[:8]}-{record_index:05d}"
        return f"RAW-{record_index:06d}"

    @staticmethod
    def raw_to_normalized_transaction(
        source_record_id: str,
        raw_payload: Dict[str, Any],
        source_dataset: str = "IBM_AML_DATA",
        raw_db_id: Optional[int] = None,
    ) -> TransactionRecord:
        """Map raw external record into normalized TransactionRecord.

        Explicitly documents mapped vs derived fields.
        """
        # IBM AML fields
        # Timestamp: '2022/09/01 00:20' or '2026-08-20'
        ts_val = raw_payload.get("Timestamp") or raw_payload.get("timestamp") or raw_payload.get("date") or raw_payload.get("transaction_date")
        txn_date = normalize_date(ts_val)

        # Amount Paid vs Amount Received
        amount_paid_raw = raw_payload.get("Amount Paid") or raw_payload.get("amount_paid") or raw_payload.get("amount") or raw_payload.get("value")
        amount = normalize_amount(amount_paid_raw)

        # Currency
        currency = str(raw_payload.get("Payment Currency") or raw_payload.get("currency") or "INR").upper()

        # Reference ID: From Account / To Account or explicit reference
        ref_id = str(
            raw_payload.get("reference_id")
            or raw_payload.get("reference")
            or raw_payload.get("Account")
            or source_record_id
        ).strip()

        cust_id = str(raw_payload.get("customer_id") or raw_payload.get("Account") or "").strip() or None
        order_id = str(raw_payload.get("order_id") or raw_payload.get("Account.1") or raw_payload.get("To Account") or "").strip() or None

        # Status: IBM dataset contains 'Is Laundering' flag or payment format; map to operational status
        is_laundering = raw_payload.get("Is Laundering") or raw_payload.get("is_laundering")
        if str(is_laundering).strip() in {"1", "true", "TRUE", "True"}:
            status = "FLAGGED_SUSPICIOUS"
        elif raw_payload.get("status"):
            status = normalize_status(raw_payload["status"])
        else:
            status = "SUCCESS"

        # Create standardized transaction ID
        txn_id = str(raw_payload.get("transaction_id") or source_record_id)
        if not txn_id.startswith("TX"):
            txn_id = f"TX_{source_record_id.replace('-', '_')}"

        return TransactionRecord(
            transaction_id=txn_id,
            source_system=source_dataset.lower(),
            amount=amount,
            currency=currency,
            transaction_date=txn_date,
            status=status,
            reference_id=ref_id,
            customer_id=cust_id,
            order_id=order_id,
            raw=dict(raw_payload),
        )

    @staticmethod
    def project_to_three_way_streams(
        normalized_records: List[TransactionRecord],
    ) -> Tuple[List[TransactionRecord], List[TransactionRecord], List[TransactionRecord]]:
        """Project normalized transactions into Payment, Bank, and Ledger streams

        for compatibility with the existing three-way reconciliation engine.

        For fields that genuine external data does not contain across all 3 legs,
        variances or missing records are preserved faithfully.
        """
        payment_stream: List[TransactionRecord] = []
        bank_stream: List[TransactionRecord] = []
        ledger_stream: List[TransactionRecord] = []

        for rec in normalized_records:
            # Payment record represents the origin payment instruction
            payment_rec = TransactionRecord(
                transaction_id=rec.transaction_id,
                source_system="payment",
                amount=rec.amount,
                currency=rec.currency,
                transaction_date=rec.transaction_date,
                status=rec.status if rec.status != "UNKNOWN" else "SUCCESS",
                reference_id=rec.reference_id,
                customer_id=rec.customer_id,
                order_id=rec.order_id,
                raw=rec.raw,
            )
            payment_stream.append(payment_rec)

            raw = rec.raw
            # Bank record represents bank clearing settlement
            # Check if Amount Received differs (e.g. cross-currency or fee)
            amount_recv = raw.get("Amount Received") or raw.get("amount_received")
            bank_amount = normalize_amount(amount_recv) if amount_recv is not None else rec.amount

            # If flagged as suspicious or custom status, reflect bank posted status
            bank_status = "FLAGGED" if rec.status == "FLAGGED_SUSPICIOUS" else "POSTED"

            bank_rec = TransactionRecord(
                transaction_id=rec.transaction_id,
                source_system="bank",
                amount=bank_amount,
                currency=str(raw.get("Receiving Currency") or rec.currency).upper(),
                transaction_date=rec.transaction_date,
                status=bank_status,
                reference_id=rec.reference_id,
                customer_id=rec.customer_id,
                order_id=rec.order_id,
                raw=raw,
            )
            bank_stream.append(bank_rec)

            # Ledger record represents internal accounting entry
            ledger_rec = TransactionRecord(
                transaction_id=rec.transaction_id,
                source_system="ledger",
                amount=rec.amount,
                currency=rec.currency,
                transaction_date=rec.transaction_date,
                status="PAID" if rec.status in {"SUCCESS", "POSTED"} else rec.status,
                reference_id=rec.reference_id,
                customer_id=rec.customer_id,
                order_id=rec.order_id,
                raw=raw,
            )
            ledger_stream.append(ledger_rec)

        return payment_stream, bank_stream, ledger_stream
