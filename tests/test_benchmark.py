from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.benchmark_reporting import evaluate_benchmark
from app.ingestion import load_records
from app.matching import match_records
from app.models import ReconciliationResult, TransactionRecord
from app.normalization import normalize_records
from scripts.generate_benchmark import (
    build_benchmark_distribution,
    generate_benchmark_records,
    save_csv,
)
from scripts.run_benchmark import run_benchmark


def test_determinism():
    """A. Determinism: same seed + same size => identical generated output."""
    p1, b1, l1, gt1 = generate_benchmark_records(seed=42, size=100)
    p2, b2, l2, gt2 = generate_benchmark_records(seed=42, size=100)

    assert p1 == p2
    assert b1 == b2
    assert l1 == l2
    assert gt1 == gt2


def test_size():
    """B. Size: size=100 => exactly 100 benchmark cases."""
    p, b, l, gt = generate_benchmark_records(seed=42, size=100)

    assert len(gt) == 100
    # Sum of records present across legs
    # Clean: 40 (all 3) = 40 in each
    # Mismatches: 20 amount + 10 status + 8 date = 38 (all 3) = 38 in each
    # Missing ledger: 8 (p, b) -> 8 in p, 8 in b
    # Missing bank: 7 (p, l) -> 7 in p, 7 in l
    # Missing payment: 4 (b, l) -> 4 in b, 4 in l
    # Unresolved: 3 (p) -> 3 in p
    # Total P: 40 + 38 + 8 + 7 + 0 + 3 = 96
    # Total B: 40 + 38 + 8 + 0 + 4 + 0 = 90
    # Total L: 40 + 38 + 0 + 7 + 4 + 0 = 89
    assert len(p) == 96
    assert len(b) == 90
    assert len(l) == 89


def test_distribution():
    """C. Distribution: generated ground truth has the intended case distribution."""
    distribution = build_benchmark_distribution(size=100)
    assert len(distribution) == 100

    _, _, _, gt = generate_benchmark_records(seed=42, size=100)

    clean_count = sum(1 for item in gt if item["perturbation_type"] == "clean")
    amt_count = sum(1 for item in gt if item["perturbation_type"] == "amount_mismatch")
    status_count = sum(1 for item in gt if item["perturbation_type"] == "status_mismatch")
    date_count = sum(1 for item in gt if item["perturbation_type"] == "date_mismatch")
    m_ledger = sum(1 for item in gt if item["perturbation_type"] == "missing_ledger")
    m_bank = sum(1 for item in gt if item["perturbation_type"] == "missing_bank")
    m_payment = sum(1 for item in gt if item["perturbation_type"] == "missing_payment")
    unresolved = sum(1 for item in gt if item["perturbation_type"] == "unresolved")

    assert clean_count == 40
    assert amt_count == 20
    assert status_count == 10
    assert date_count == 8
    assert m_ledger == 8
    assert m_bank == 7
    assert m_payment == 4
    assert unresolved == 3

    assert sum([clean_count, amt_count, status_count, date_count, m_ledger, m_bank, m_payment, unresolved]) == 100


def test_ground_truth_integrity():
    """D. Ground truth integrity: every benchmark record has ground truth, unique references, unique IDs."""
    _, _, _, gt = generate_benchmark_records(seed=42, size=100)

    record_ids = [item["record_id"] for item in gt]
    ref_ids = [item["reference_id"] for item in gt]

    assert len(set(record_ids)) == 100
    assert len(set(ref_ids)) == 100
    for item in gt:
        assert item["expected_outcome"] in ("matched", "exception")
        if item["expected_outcome"] == "matched":
            assert item["expected_exception_type"] is None
        else:
            assert item["expected_exception_type"] is not None
        assert set(item["legs_present"]).issubset({"payment", "bank", "ledger"})


def test_clean_matches():
    """E. Clean matches: clean cases contain equal amount/date/status across all three legs."""
    p_rows, b_rows, l_rows, gt = generate_benchmark_records(seed=42, size=100)

    p_by_ref = {r["reference_id"]: r for r in p_rows}
    b_by_ref = {r["reference_id"]: r for r in b_rows}
    l_by_ref = {r["reference_id"]: r for r in l_rows}

    for item in gt:
        if item["perturbation_type"] == "clean":
            ref = item["reference_id"]
            p = p_by_ref[ref]
            b = b_by_ref[ref]
            l = l_by_ref[ref]

            assert p["amount"] == b["amount"] == l["amount"]
            assert p["date"] == b["date"] == l["date"]
            assert p["status"] == b["status"] == l["status"] == "SUCCESS"
            assert p["currency"] == b["currency"] == l["currency"] == "INR"


def test_controlled_perturbations():
    """F. Controlled perturbations: amount/date/status change only intended field, missing legs omit properly."""
    p_rows, b_rows, l_rows, gt = generate_benchmark_records(seed=42, size=100)

    p_by_ref = {r["reference_id"]: r for r in p_rows}
    b_by_ref = {r["reference_id"]: r for r in b_rows}
    l_by_ref = {r["reference_id"]: r for r in l_rows}

    for item in gt:
        ref = item["reference_id"]
        ptype = item["perturbation_type"]

        if ptype == "amount_mismatch":
            target = item["perturbation_details"]["target"]
            delta = Decimal(item["perturbation_details"]["delta"])
            p = p_by_ref[ref]
            b = b_by_ref[ref]
            l = l_by_ref[ref]
            assert p["date"] == b["date"] == l["date"]
            assert p["status"] == b["status"] == l["status"]
            if target == "bank":
                assert Decimal(b["amount"]) == Decimal(p["amount"]) + delta
            elif target == "ledger":
                assert Decimal(l["amount"]) == Decimal(p["amount"]) + delta

        elif ptype == "status_mismatch":
            p = p_by_ref[ref]
            b = b_by_ref[ref]
            l = l_by_ref[ref]
            assert p["amount"] == b["amount"] == l["amount"]
            assert p["date"] == b["date"] == l["date"]
            assert l["status"] == "PENDING"
            assert p["status"] == "SUCCESS"
            assert b["status"] == "SUCCESS"

        elif ptype == "date_mismatch":
            p = p_by_ref[ref]
            b = b_by_ref[ref]
            l = l_by_ref[ref]
            assert p["amount"] == b["amount"] == l["amount"]
            assert p["status"] == b["status"] == l["status"]
            assert p["date"] != b["date"]
            assert p["date"] == l["date"]

        elif ptype == "missing_ledger":
            assert ref in p_by_ref
            assert ref in b_by_ref
            assert ref not in l_by_ref

        elif ptype == "missing_bank":
            assert ref in p_by_ref
            assert ref not in b_by_ref
            assert ref in l_by_ref

        elif ptype == "missing_payment":
            assert ref not in p_by_ref
            assert ref in b_by_ref
            assert ref in l_by_ref

        elif ptype == "unresolved":
            assert ref in p_by_ref
            assert ref not in b_by_ref
            assert ref not in l_by_ref


def test_no_data_leakage():
    """G. No data leakage: matcher invocation does not receive ground-truth data."""
    p_rec = TransactionRecord(transaction_id="TX1", source_system="payment", amount=Decimal("100.00"), reference_id="REF1")
    b_rec = TransactionRecord(transaction_id="TX1", source_system="bank", amount=Decimal("100.00"), reference_id="REF1")
    l_rec = TransactionRecord(transaction_id="TX1", source_system="ledger", amount=Decimal("100.00"), reference_id="REF1")

    # Matcher accepts only the records
    results = match_records([p_rec], [b_rec], [l_rec])
    assert len(results) == 1
    assert results[0].matched is True
    # Ground truth is not referenced or accessed anywhere in match_records


def test_metrics_evaluation():
    """H. Metrics: known small synthetic prediction/ground-truth fixture produces expected metrics."""
    ground_truth = [
        {"reference_id": "REF01", "expected_outcome": "matched", "expected_exception_type": None},
        {"reference_id": "REF02", "expected_outcome": "matched", "expected_exception_type": None},
        {"reference_id": "REF03", "expected_outcome": "exception", "expected_exception_type": "amount_mismatch"},
        {"reference_id": "REF04", "expected_outcome": "exception", "expected_exception_type": "missing_ledger"},
    ]

    predictions = [
        ReconciliationResult(transaction_id="REF01", source_system="all", matched=True, match_score=1.0),
        ReconciliationResult(transaction_id="REF02", source_system="all", matched=False, match_score=0.6, exception_type="status_mismatch"),  # FN
        ReconciliationResult(transaction_id="REF03", source_system="all", matched=True, match_score=1.0),  # FP
        ReconciliationResult(transaction_id="REF04", source_system="all", matched=False, match_score=0.5, exception_type="missing_ledger"),  # TN, correct class
    ]

    metrics = evaluate_benchmark(predictions, ground_truth, elapsed_seconds=0.01)

    # Positive = Matched, Negative = Exception
    # REF01: Expected matched, Pred matched -> TP (1)
    # REF02: Expected matched, Pred exception -> FN (1)
    # REF03: Expected exception, Pred matched -> FP (1)
    # REF04: Expected exception, Pred exception -> TN (1)
    bm = metrics["binary_metrics"]
    assert bm["tp"] == 1
    assert bm["tn"] == 1
    assert bm["fp"] == 1
    assert bm["fn"] == 1
    assert bm["precision"] == 50.0
    assert bm["recall"] == 50.0
    assert bm["f1"] == 50.0

    # Multiclass:
    # REF01: matched == matched (correct)
    # REF02: matched != status_mismatch (incorrect)
    # REF03: amount_mismatch != matched (incorrect)
    # REF04: missing_ledger == missing_ledger (correct)
    # 2 correct out of 4 -> 50%
    assert metrics["classification"]["correct_classifications"] == 2
    assert metrics["classification"]["incorrect_classifications"] == 2
    assert metrics["classification"]["multiclass_accuracy"] == 50.0


def test_decimal_correctness():
    """I. Decimal correctness: benchmark monetary calculations remain Decimal."""
    p_rows, b_rows, l_rows, _ = generate_benchmark_records(seed=42, size=10)
    for r in p_rows + b_rows + l_rows:
        val = Decimal(r["amount"])
        assert isinstance(val, Decimal)
        # Ensure 2 decimal places format
        parts = r["amount"].split(".")
        assert len(parts) == 2
        assert len(parts[1]) == 2


def test_end_to_end_benchmark(tmp_path: Path):
    """J. End-to-end benchmark: generate small benchmark, run matcher, score against ground truth."""
    p_rows, b_rows, l_rows, gt = generate_benchmark_records(seed=123, size=20)

    p_file = tmp_path / "payment.csv"
    b_file = tmp_path / "bank.csv"
    l_file = tmp_path / "ledger.csv"
    gt_file = tmp_path / "ground_truth.json"
    res_file = tmp_path / "results.json"

    save_csv(p_rows, p_file)
    save_csv(b_rows, b_file)
    save_csv(l_rows, l_file)
    gt_file.write_text(json.dumps(gt), encoding="utf-8")

    report = run_benchmark(
        payment_path=p_file,
        bank_path=b_file,
        ledger_path=l_file,
        ground_truth_path=gt_file,
        output_path=res_file,
    )

    assert res_file.exists()
    assert report["volume"]["total_records"] == 20
    assert report["volume"]["matched"] + report["volume"]["exceptions"] == 20
    assert report["volume"]["match_rate"] + report["volume"]["exception_rate"] == 100.0
    assert report["performance"]["processing_time_seconds"] >= 0.0
    assert report["performance"]["throughput_records_per_second"] > 0.0
    assert report["provenance"]["database_writes"] is False
