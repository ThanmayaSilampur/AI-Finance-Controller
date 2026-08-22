from __future__ import annotations

from typing import Dict, List, Sequence

from app.models import ReconciliationResult, TransactionRecord
from app.normalization import normalize_date, normalize_status


def exact_match_key(record: TransactionRecord) -> str:
    return (record.reference_id or record.transaction_id or "").strip()


def _effective_status(record: TransactionRecord) -> str:
    if record.status and str(record.status).strip():
        return normalize_status(record.status)
    if record.raw:
        return normalize_status(record.raw.get("status"))
    return "UNKNOWN"


def _effective_date(record: TransactionRecord):
    if record.transaction_date is not None:
        return record.transaction_date
    if not record.raw:
        return None
    return normalize_date(record.raw.get("transaction_date") or record.raw.get("date"))


def _classify_all_records(payment: TransactionRecord, bank: TransactionRecord, ledger: TransactionRecord) -> tuple[bool, str, str, float, dict]:
    amount_values = [item.amount for item in [payment, bank, ledger] if item]
    if len(set(amount_values)) > 1:
        return False, "amount_mismatch", "review_amount_variance", 0.6, {"amounts": [str(value) for value in amount_values]}

    dates = {_effective_date(item) for item in [payment, bank, ledger] if item and _effective_date(item) is not None}
    if len(dates) > 1:
        return False, "date_mismatch", "check_transaction_dates", 0.75, {"dates": [str(value) for value in sorted(dates, key=lambda d: str(d))]}

    statuses = {_effective_status(item) for item in [payment, bank, ledger] if item}
    if len(statuses) > 1:
        return False, "status_mismatch", "verify_statuses", 0.7, {"statuses": sorted(statuses)}

    return True, None, "confirm_and_close", 1.0, {"amount": str(payment.amount)}


def match_records(payment_records: Sequence[TransactionRecord], bank_records: Sequence[TransactionRecord], ledger_records: Sequence[TransactionRecord]) -> List[ReconciliationResult]:
    """Match transaction records across the three sources using deterministic finance rules."""
    payment_by_id: Dict[str, TransactionRecord] = {exact_match_key(record): record for record in payment_records}
    bank_by_id: Dict[str, TransactionRecord] = {exact_match_key(record): record for record in bank_records}
    ledger_by_id: Dict[str, TransactionRecord] = {exact_match_key(record): record for record in ledger_records}

    results: List[ReconciliationResult] = []
    all_ids = sorted(set(payment_by_id) | set(bank_by_id) | set(ledger_by_id))

    for txn_id in all_ids:
        payment = payment_by_id.get(txn_id)
        bank = bank_by_id.get(txn_id)
        ledger = ledger_by_id.get(txn_id)

        if payment and bank and ledger:
            matched, exception_type, recommended_action, score, details = _classify_all_records(payment, bank, ledger)
            results.append(
                ReconciliationResult(
                    transaction_id=txn_id,
                    source_system="all",
                    matched=matched,
                    match_score=score,
                    exception_type=exception_type,
                    explanations=[
                        "All three sources share the same transaction ID.",
                    ] if matched else [
                        "One or more financial fields differ across sources.",
                    ],
                    recommended_action=recommended_action,
                    details=details,
                )
            )
            continue

        if payment and bank and not ledger:
            results.append(
                ReconciliationResult(
                    transaction_id=txn_id,
                    source_system="payment+bank",
                    matched=False,
                    match_score=0.5,
                    exception_type="missing_ledger",
                    explanations=["A payment and bank record exist, but the ledger entry is missing."],
                    recommended_action="check_missing_ledger_entry",
                    details={},
                )
            )
            continue

        if payment and ledger and not bank:
            results.append(
                ReconciliationResult(
                    transaction_id=txn_id,
                    source_system="payment+ledger",
                    matched=False,
                    match_score=0.5,
                    exception_type="missing_bank",
                    explanations=["A payment and ledger record exist, but the bank record is missing."],
                    recommended_action="check_missing_bank_record",
                    details={},
                )
            )
            continue

        if bank and ledger and not payment:
            results.append(
                ReconciliationResult(
                    transaction_id=txn_id,
                    source_system="bank+ledger",
                    matched=False,
                    match_score=0.4,
                    exception_type="missing_payment",
                    explanations=["A bank and ledger record exist, but the payment record is missing."],
                    recommended_action="trace_missing_payment",
                    details={},
                )
            )
            continue

        if payment:
            results.append(
                ReconciliationResult(
                    transaction_id=txn_id,
                    source_system="payment",
                    matched=False,
                    match_score=0.1,
                    exception_type="unresolved",
                    explanations=["No matching counterpart was found for the payment record."],
                    recommended_action="manual_review",
                    details={},
                )
            )

    return results
