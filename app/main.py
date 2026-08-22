from __future__ import annotations

from pathlib import Path

from app.ingestion import load_records
from app.matching import match_records
from app.normalization import normalize_records


def run_reconciliation(data_dir: str | Path = "data") -> list:
    data_path = Path(data_dir)
    payment_records = normalize_records(load_records(data_path / "sample_payment.csv", "payment"))
    bank_records = normalize_records(load_records(data_path / "sample_bank.csv", "bank"))
    ledger_records = normalize_records(load_records(data_path / "sample_ledger.csv", "ledger"))

    results = match_records(payment_records, bank_records, ledger_records)
    matched = sum(1 for item in results if item.matched)
    unresolved = sum(1 for item in results if not item.matched)

    print(f"Total reconciled records: {len(results)}")
    print(f"Matched: {matched}")
    print(f"Unresolved: {unresolved}")
    for result in results:
        print(f"{result.transaction_id}: matched={result.matched}, exception={result.exception_type}, action={result.recommended_action}")

    return results


if __name__ == "__main__":
    run_reconciliation()
