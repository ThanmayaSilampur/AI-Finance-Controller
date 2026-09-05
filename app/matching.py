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


def _classify_all_records(
    payment: TransactionRecord,
    bank: TransactionRecord,
    ledger: TransactionRecord,
    max_date_variance_days: int = 0,
) -> tuple[bool, str, str, float, dict]:
    amount_values = [item.amount for item in [payment, bank, ledger] if item]
    if len(set(amount_values)) > 1:
        return False, "amount_mismatch", "review_amount_variance", 0.6, {"amounts": [str(value) for value in amount_values]}

    dates = [_effective_date(item) for item in [payment, bank, ledger] if item and _effective_date(item) is not None]
    if len(set(dates)) > 1:
        try:
            min_date = min(dates)
            max_date = max(dates)
            delta_days = (max_date - min_date).days
            if delta_days > max_date_variance_days:
                return False, "date_mismatch", "check_transaction_dates", 0.75, {
                    "dates": [str(value) for value in sorted(set(dates), key=lambda d: str(d))],
                    "variance_days": delta_days,
                }
        except Exception:
            return False, "date_mismatch", "check_transaction_dates", 0.75, {
                "dates": [str(value) for value in sorted(set(dates), key=lambda d: str(d))]
            }

    statuses = {_effective_status(item) for item in [payment, bank, ledger] if item}
    if len(statuses) > 1:
        return False, "status_mismatch", "verify_statuses", 0.7, {"statuses": sorted(statuses)}

    details = {"amount": str(payment.amount)}
    if len(set(dates)) > 1:
        details["settlement_lag_days"] = (max(dates) - min(dates)).days
        details["note"] = f"Cleared within permissible T+{max_date_variance_days} settlement window."

    return True, None, "confirm_and_close", 1.0, details


def _index_records(
    records: Sequence[TransactionRecord], stream_name: str
) -> tuple[Dict[str, TransactionRecord], Dict[str, List[TransactionRecord]]]:
    """Index records by exact match key while detecting in-source duplicate reference collisions."""
    indexed: Dict[str, TransactionRecord] = {}
    duplicates: Dict[str, List[TransactionRecord]] = {}
    for record in records:
        key = exact_match_key(record)
        if key in indexed:
            if key not in duplicates:
                duplicates[key] = [indexed[key]]
            duplicates[key].append(record)
        else:
            indexed[key] = record
    return indexed, duplicates


def match_records(
    payment_records: Sequence[TransactionRecord],
    bank_records: Sequence[TransactionRecord],
    ledger_records: Sequence[TransactionRecord],
    max_date_variance_days: int = 0,
) -> List[ReconciliationResult]:
    """Match transaction records across the three sources using deterministic finance rules.
    
    Supports:
    - In-source duplicate reference collision isolation (`duplicate_reference`)
    - Configurable settlement clearing window tolerance (`max_date_variance_days`)
    """
    payment_by_id, payment_dups = _index_records(payment_records, "payment")
    bank_by_id, bank_dups = _index_records(bank_records, "bank")
    ledger_by_id, ledger_dups = _index_records(ledger_records, "ledger")

    results: List[ReconciliationResult] = []
    all_ids = sorted(set(payment_by_id) | set(bank_by_id) | set(ledger_by_id))

    for txn_id in all_ids:
        # Check for in-source duplicate collision
        has_dup = txn_id in payment_dups or txn_id in bank_dups or txn_id in ledger_dups
        if has_dup:
            dup_sources = []
            if txn_id in payment_dups:
                dup_sources.append(f"payment ({len(payment_dups[txn_id])} records)")
            if txn_id in bank_dups:
                dup_sources.append(f"bank ({len(bank_dups[txn_id])} records)")
            if txn_id in ledger_dups:
                dup_sources.append(f"ledger ({len(ledger_dups[txn_id])} records)")
            
            results.append(
                ReconciliationResult(
                    transaction_id=txn_id,
                    source_system="duplicate_collision",
                    matched=False,
                    match_score=0.2,
                    exception_type="duplicate_reference",
                    explanations=[
                        f"Duplicate reference ID detected in source data: {', '.join(dup_sources)}."
                    ],
                    recommended_action="investigate_duplicate_entries",
                    details={"duplicates": dup_sources},
                )
            )
            continue

        payment = payment_by_id.get(txn_id)
        bank = bank_by_id.get(txn_id)
        ledger = ledger_by_id.get(txn_id)

        if payment and bank and ledger:
            matched, exception_type, recommended_action, score, details = _classify_all_records(
                payment, bank, ledger, max_date_variance_days=max_date_variance_days
            )
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
            continue

        if bank:
            results.append(
                ReconciliationResult(
                    transaction_id=txn_id,
                    source_system="bank",
                    matched=False,
                    match_score=0.1,
                    exception_type="unresolved",
                    explanations=["Unreconciled bank deposit without payment or ledger counterpart."],
                    recommended_action="manual_review",
                    details={},
                )
            )
            continue

        if ledger:
            results.append(
                ReconciliationResult(
                    transaction_id=txn_id,
                    source_system="ledger",
                    matched=False,
                    match_score=0.1,
                    exception_type="unresolved",
                    explanations=["Unreconciled ledger entry without payment or bank counterpart."],
                    recommended_action="manual_review",
                    details={},
                )
            )

    return results
