#!/usr/bin/env python3
"""Standalone benchmark runner for reconciliation engine.

Runs matching purely in-memory using the existing deterministic matcher without DB access.
Measures matching throughput accurately and evaluates predictions against segregated ground truth.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.benchmark_reporting import evaluate_benchmark
from app.ingestion import load_records
from app.matching import match_records
from app.normalization import normalize_records


def run_benchmark(
    payment_path: Path,
    bank_path: Path,
    ledger_path: Path,
    ground_truth_path: Path,
    output_path: Path | None = None,
) -> Dict[str, Any]:
    """Execute reconciliation benchmark without database dependencies."""
    if not payment_path.exists():
        raise FileNotFoundError(f"Payment CSV not found: {payment_path}")
    if not bank_path.exists():
        raise FileNotFoundError(f"Bank CSV not found: {bank_path}")
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger CSV not found: {ledger_path}")
    if not ground_truth_path.exists():
        raise FileNotFoundError(f"Ground truth JSON not found: {ground_truth_path}")

    # 1. Ingestion & normalization via standard application paths
    raw_payment = load_records(payment_path, source_system="payment")
    raw_bank = load_records(bank_path, source_system="bank")
    raw_ledger = load_records(ledger_path, source_system="ledger")

    norm_payment = normalize_records(raw_payment)
    norm_bank = normalize_records(raw_bank)
    norm_ledger = normalize_records(raw_ledger)

    # 2. Reconcile - ONLY measure the matching operation
    start_time = time.perf_counter()
    predictions = match_records(norm_payment, norm_bank, norm_ledger)
    elapsed_time = time.perf_counter() - start_time

    # 3. Load ground truth strictly AFTER reconciliation has completed
    ground_truth_data = json.loads(ground_truth_path.read_text(encoding="utf-8"))

    # 4. Evaluate predictions against ground truth
    metrics = evaluate_benchmark(
        predictions=predictions,
        ground_truth=ground_truth_data,
        elapsed_seconds=elapsed_time,
    )

    # 5. Build structured benchmark output
    first_row = ground_truth_data[0] if ground_truth_data else {}
    report = {
        "benchmark": {
            "dataset_version": "v1.0",
            "size": len(ground_truth_data),
        },
        "provenance": {
            "source": "SYNTHETIC_BENCHMARK",
            "derived_records": True,
            "ground_truth_external_to_matcher": True,
            "database_writes": False,
        },
        "volume": metrics["volume"],
        "classification": metrics["classification"],
        "exception_accuracy": metrics["exception_accuracy"],
        "binary_metrics": metrics["binary_metrics"],
        "breakdown": metrics["breakdown"],
        "performance": metrics["performance"],
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reconciliation benchmark against synthetic dataset.")
    parser.add_argument("--payment", type=str, default="data/benchmark_payment.csv", help="Payment CSV path")
    parser.add_argument("--bank", type=str, default="data/benchmark_bank.csv", help="Bank CSV path")
    parser.add_argument("--ledger", type=str, default="data/benchmark_ledger.csv", help="Ledger CSV path")
    parser.add_argument("--ground-truth", type=str, default="data/benchmark_ground_truth.json", help="Ground truth JSON path")
    parser.add_argument("--output", type=str, default="data/benchmark_results.json", help="Benchmark output JSON path")

    args = parser.parse_args()

    report = run_benchmark(
        payment_path=Path(args.payment),
        bank_path=Path(args.bank),
        ledger_path=Path(args.ledger),
        ground_truth_path=Path(args.ground_truth),
        output_path=Path(args.output),
    )

    print("=" * 60)
    print("RECONCILIATION BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total Records:         {report['volume']['total_records']}")
    print(f"Matched:               {report['volume']['matched']} ({report['volume']['match_rate']}%)")
    print(f"Exceptions:            {report['volume']['exceptions']} ({report['volume']['exception_rate']}%)")
    print(f"Multiclass Accuracy:   {report['classification']['multiclass_accuracy']}%")
    print(f"Binary F1 Score:       {report['binary_metrics']['f1']}%")
    print(f"Macro F1 Score:        {report['binary_metrics']['macro_f1']}%")
    print(f"Elapsed Time:          {report['performance']['processing_time_seconds']}s")
    print(f"Throughput:            {report['performance']['throughput_records_per_second']} records/sec")
    print("=" * 60)
    print(f"Detailed results saved to: {args.output}")


if __name__ == "__main__":
    main()
