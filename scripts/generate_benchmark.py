#!/usr/bin/env python3
"""Pure-Python deterministic benchmark generator for reconciliation benchmarking.

Produces synthetic 3-way reconciliation datasets (payment, bank, ledger) and
independent ground truth for testing reconciliation engine performance without database writes.
"""

from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _format_decimal(val: Decimal) -> str:
    """Format decimal amount strictly with 2 decimal places."""
    return f"{val:.2f}"


def build_benchmark_distribution(size: int = 100) -> List[Tuple[str, Dict[str, Any]]]:
    """Define deterministic benchmark cases for the specified size.

    For size == 100, exactly matches the required distribution:
    - 40 clean matches
    - 12 amount mismatch (bank lower)
    - 8 amount mismatch (ledger lower)
    - 10 status mismatch (ledger status PENDING)
    - 8 date mismatch (bank date +1 day)
    - 8 missing ledger
    - 7 missing bank
    - 4 missing payment
    - 3 unresolved / payment-only
    """
    if size == 100:
        specs: List[Tuple[str, Dict[str, Any]]] = []
        specs.extend([("clean", {}) for _ in range(40)])
        specs.extend([("amount_mismatch", {"target": "bank", "delta": Decimal("-150.00")}) for _ in range(12)])
        specs.extend([("amount_mismatch", {"target": "ledger", "delta": Decimal("-200.00")}) for _ in range(8)])
        specs.extend([("status_mismatch", {"target": "ledger", "status": "PENDING"}) for _ in range(10)])
        specs.extend([("date_mismatch", {"target": "bank", "day_offset": 1}) for _ in range(8)])
        specs.extend([("missing_ledger", {}) for _ in range(8)])
        specs.extend([("missing_bank", {}) for _ in range(7)])
        specs.extend([("missing_payment", {}) for _ in range(4)])
        specs.extend([("unresolved", {}) for _ in range(3)])
        return specs

    # Proportional scaling fallback if size != 100
    base_counts = [
        ("clean", {}, 40),
        ("amount_mismatch", {"target": "bank", "delta": Decimal("-150.00")}, 12),
        ("amount_mismatch", {"target": "ledger", "delta": Decimal("-200.00")}, 8),
        ("status_mismatch", {"target": "ledger", "status": "PENDING"}, 10),
        ("date_mismatch", {"target": "bank", "day_offset": 1}, 8),
        ("missing_ledger", {}, 8),
        ("missing_bank", {}, 7),
        ("missing_payment", {}, 4),
        ("unresolved", {}, 3),
    ]
    specs = []
    accumulated = 0
    for name, params, weight in base_counts:
        count = max(1, int(round(weight * size / 100.0)))
        if accumulated + count > size:
            count = max(0, size - accumulated)
        specs.extend([(name, params) for _ in range(count)])
        accumulated += count
    while len(specs) < size:
        specs.append(("clean", {}))
    return specs[:size]


def generate_benchmark_records(
    seed: int = 42,
    size: int = 100,
) -> Tuple[List[dict], List[dict], List[dict], List[dict]]:
    """Deterministically generate payment, bank, ledger rows and ground-truth metadata.

    Mapping: (seed, record_index) -> canonical record + controlled perturbation.
    """
    distribution = build_benchmark_distribution(size)

    payment_rows: List[dict] = []
    bank_rows: List[dict] = []
    ledger_rows: List[dict] = []
    ground_truth: List[dict] = []

    for idx, (perturbation_type, params) in enumerate(distribution, start=1):
        record_id = f"BM-{idx:03d}"
        ref_id = f"REF{idx:04d}"

        # Deterministic base amount derived from seed & index using integer arithmetic
        base_cents = 100000 + ((seed * 10007 + idx * 7919) % 4900000)
        base_amount = Decimal(base_cents) / Decimal(100)

        # Base date deterministically selected in August 2026 (day 1..20)
        day = 1 + ((seed * 31 + idx * 17) % 20)
        base_date = f"2026-08-{day:02d}"

        canonical_status = "SUCCESS"
        canonical_currency = "INR"

        provenance = {
            "source": "SYNTHETIC_BENCHMARK",
            "dataset_version": "v1.0",
            "seed": seed,
            "record_index": idx,
            "derivation": "controlled_perturbation",
        }

        # Initialize legs from canonical definition
        p_amount = base_amount
        b_amount = base_amount
        l_amount = base_amount

        p_date = base_date
        b_date = base_date
        l_date = base_date

        p_status = canonical_status
        b_status = canonical_status
        l_status = canonical_status

        expected_outcome = "matched"
        expected_exception_type = None
        perturbation_details: Dict[str, Any] = {}
        legs_present = ["payment", "bank", "ledger"]

        if perturbation_type == "clean":
            expected_outcome = "matched"
            expected_exception_type = None

        elif perturbation_type == "amount_mismatch":
            expected_outcome = "exception"
            expected_exception_type = "amount_mismatch"
            target = params["target"]
            delta = params["delta"]
            perturbation_details = {"target": target, "delta": str(delta)}
            if target == "bank":
                b_amount = base_amount + delta
            elif target == "ledger":
                l_amount = base_amount + delta

        elif perturbation_type == "status_mismatch":
            expected_outcome = "exception"
            expected_exception_type = "status_mismatch"
            target = params["target"]
            new_status = params["status"]
            perturbation_details = {"target": target, "status": new_status}
            if target == "ledger":
                l_status = new_status

        elif perturbation_type == "date_mismatch":
            expected_outcome = "exception"
            expected_exception_type = "date_mismatch"
            target = params["target"]
            offset = params["day_offset"]
            perturbation_details = {"target": target, "day_offset": offset}
            if target == "bank":
                b_date = f"2026-08-{(day + offset):02d}"

        elif perturbation_type == "missing_ledger":
            expected_outcome = "exception"
            expected_exception_type = "missing_ledger"
            legs_present = ["payment", "bank"]

        elif perturbation_type == "missing_bank":
            expected_outcome = "exception"
            expected_exception_type = "missing_bank"
            legs_present = ["payment", "ledger"]

        elif perturbation_type == "missing_payment":
            expected_outcome = "exception"
            expected_exception_type = "missing_payment"
            legs_present = ["bank", "ledger"]

        elif perturbation_type == "unresolved":
            expected_outcome = "exception"
            expected_exception_type = "unresolved"
            legs_present = ["payment"]

        # Append legs according to presence
        if "payment" in legs_present:
            payment_rows.append({
                "transaction_id": ref_id,
                "reference_id": ref_id,
                "amount": _format_decimal(p_amount),
                "date": p_date,
                "status": p_status,
                "currency": canonical_currency,
                "customer_id": f"CUST{idx:04d}",
                "order_id": f"ORD{idx:04d}",
                "source_dataset": "BENCHMARK_V1",
                "provenance": json.dumps(provenance),
            })

        if "bank" in legs_present:
            bank_rows.append({
                "transaction_id": ref_id,
                "reference_id": ref_id,
                "amount": _format_decimal(b_amount),
                "date": b_date,
                "status": b_status,
                "currency": canonical_currency,
                "customer_id": f"CUST{idx:04d}",
                "order_id": f"ORD{idx:04d}",
                "source_dataset": "BENCHMARK_V1",
                "provenance": json.dumps(provenance),
            })

        if "ledger" in legs_present:
            ledger_rows.append({
                "transaction_id": ref_id,
                "reference_id": ref_id,
                "amount": _format_decimal(l_amount),
                "date": l_date,
                "status": l_status,
                "currency": canonical_currency,
                "customer_id": f"CUST{idx:04d}",
                "order_id": f"ORD{idx:04d}",
                "source_dataset": "BENCHMARK_V1",
                "provenance": json.dumps(provenance),
            })

        ground_truth.append({
            "record_id": record_id,
            "reference_id": ref_id,
            "perturbation_type": perturbation_type,
            "perturbation_details": perturbation_details,
            "expected_outcome": expected_outcome,
            "expected_exception_type": expected_exception_type,
            "legs_present": legs_present,
        })

    return payment_rows, bank_rows, ledger_rows, ground_truth


def save_csv(rows: List[dict], filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with filepath.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic benchmark data for reconciliation.")
    parser.add_argument("--seed", type=int, default=42, help="Seed for deterministic generation (default: 42)")
    parser.add_argument("--size", type=int, default=100, help="Number of benchmark records (default: 100)")
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory for generated files")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    p_rows, b_rows, l_rows, gt = generate_benchmark_records(seed=args.seed, size=args.size)

    p_file = out_dir / "benchmark_payment.csv"
    b_file = out_dir / "benchmark_bank.csv"
    l_file = out_dir / "benchmark_ledger.csv"
    gt_file = out_dir / "benchmark_ground_truth.json"

    save_csv(p_rows, p_file)
    save_csv(b_rows, b_file)
    save_csv(l_rows, l_file)

    out_dir.mkdir(parents=True, exist_ok=True)
    gt_file.write_text(json.dumps(gt, indent=2), encoding="utf-8")

    print(f"Generated benchmark files successfully (seed={args.seed}, size={args.size}):")
    print(f" - Payment records: {len(p_rows)} -> {p_file}")
    print(f" - Bank records:    {len(b_rows)} -> {b_file}")
    print(f" - Ledger records:  {len(l_rows)} -> {l_file}")
    print(f" - Ground truth:    {len(gt)} records -> {gt_file}")


if __name__ == "__main__":
    main()
