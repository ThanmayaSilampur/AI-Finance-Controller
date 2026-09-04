from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from app.models import ReconciliationResult


def evaluate_benchmark(
    predictions: Sequence[ReconciliationResult],
    ground_truth: Sequence[Dict[str, Any]],
    elapsed_seconds: float = 0.0,
) -> Dict[str, Any]:
    """Evaluate reconciliation predictions against independent ground truth.

    Computes volume metrics, classification accuracy, per-class exception confusion,
    binary detection statistics (Matched vs Exception), and throughput.
    """
    truth_by_ref: Dict[str, Dict[str, Any]] = {
        gt["reference_id"]: gt for gt in ground_truth
    }

    total_records = len(ground_truth)
    pred_by_ref: Dict[str, ReconciliationResult] = {
        pred.transaction_id: pred for pred in predictions
    }

    # Volume counts from matcher output
    matched_count = sum(1 for p in predictions if p.matched)
    exception_count = sum(1 for p in predictions if not p.matched)

    match_rate = round((matched_count / total_records) * 100, 4) if total_records else 0.0
    exception_rate = round((exception_count / total_records) * 100, 4) if total_records else 0.0

    # Binary metrics: Positive = Matched (clean), Negative = Exception / Unresolved
    tp = 0  # Expected matched and predicted matched
    fp = 0  # Expected exception but predicted matched
    fn = 0  # Expected matched but predicted exception
    tn = 0  # Expected exception and predicted exception

    # Classification & Exception metrics
    correct_classifications = 0
    incorrect_classifications = 0

    expected_exception_counts = Counter()
    predicted_exception_counts = Counter()
    per_class_performance: Dict[str, Dict[str, int]] = {}

    all_known_classes = [
        "matched",
        "amount_mismatch",
        "date_mismatch",
        "status_mismatch",
        "missing_ledger",
        "missing_bank",
        "missing_payment",
        "unresolved",
    ]

    for cls_name in all_known_classes:
        per_class_performance[cls_name] = {
            "expected": 0,
            "predicted": 0,
            "true_positive": 0,
            "false_positive": 0,
            "false_negative": 0,
        }

    for ref_id, gt in truth_by_ref.items():
        expected_outcome = gt["expected_outcome"]  # "matched" or "exception"
        expected_exception = gt.get("expected_exception_type")
        expected_class = "matched" if expected_outcome == "matched" else (expected_exception or "unresolved")

        if expected_class in per_class_performance:
            per_class_performance[expected_class]["expected"] += 1
        if expected_exception:
            expected_exception_counts[expected_exception] += 1

        pred = pred_by_ref.get(ref_id)
        if pred is None:
            # Missing in predictions entirely
            pred_class = "unresolved"
            pred_outcome = "exception"
        else:
            pred_outcome = "matched" if pred.matched else "exception"
            pred_class = "matched" if pred.matched else (pred.exception_type or "unresolved")

        if pred_class in per_class_performance:
            per_class_performance[pred_class]["predicted"] += 1
        if pred_outcome == "exception" and pred and pred.exception_type:
            predicted_exception_counts[pred.exception_type] += 1

        # Binary confusion matrix (Positive = Matched)
        if expected_outcome == "matched" and pred_outcome == "matched":
            tp += 1
        elif expected_outcome == "exception" and pred_outcome == "matched":
            fp += 1
        elif expected_outcome == "matched" and pred_outcome == "exception":
            fn += 1
        elif expected_outcome == "exception" and pred_outcome == "exception":
            tn += 1

        # Multiclass evaluation
        if expected_class == pred_class:
            correct_classifications += 1
            if expected_class in per_class_performance:
                per_class_performance[expected_class]["true_positive"] += 1
        else:
            incorrect_classifications += 1
            if expected_class in per_class_performance:
                per_class_performance[expected_class]["false_negative"] += 1
            if pred_class in per_class_performance:
                per_class_performance[pred_class]["false_positive"] += 1

    # Multiclass accuracy
    multiclass_accuracy = round((correct_classifications / total_records) * 100, 4) if total_records else 0.0

    # Binary precision, recall, F1
    precision = round((tp / (tp + fp)) * 100, 4) if (tp + fp) > 0 else 0.0
    recall = round((tp / (tp + fn)) * 100, 4) if (tp + fn) > 0 else 0.0
    f1 = round((2 * precision * recall / (precision + recall)), 4) if (precision + recall) > 0 else 0.0

    # Macro Precision, Recall, F1 across active classes
    precisions_list = []
    recalls_list = []
    f1_list = []

    for cls_name, stats in per_class_performance.items():
        c_tp = stats["true_positive"]
        c_fp = stats["false_positive"]
        c_fn = stats["false_negative"]
        c_prec = (c_tp / (c_tp + c_fp)) if (c_tp + c_fp) > 0 else (1.0 if stats["expected"] == 0 else 0.0)
        c_rec = (c_tp / (c_tp + c_fn)) if (c_tp + c_fn) > 0 else (1.0 if stats["expected"] == 0 else 0.0)
        c_f1 = (2 * c_prec * c_rec / (c_prec + c_rec)) if (c_prec + c_rec) > 0 else 0.0

        stats["precision"] = round(c_prec * 100, 2)
        stats["recall"] = round(c_rec * 100, 2)
        stats["f1"] = round(c_f1 * 100, 2)

        if stats["expected"] > 0 or stats["predicted"] > 0:
            precisions_list.append(c_prec)
            recalls_list.append(c_rec)
            f1_list.append(c_f1)

    macro_precision = round((sum(precisions_list) / len(precisions_list)) * 100, 4) if precisions_list else 0.0
    macro_recall = round((sum(recalls_list) / len(recalls_list)) * 100, 4) if recalls_list else 0.0
    macro_f1 = round((sum(f1_list) / len(f1_list)) * 100, 4) if f1_list else 0.0

    # Throughput
    throughput = round(total_records / elapsed_seconds, 2) if elapsed_seconds > 0 else 0.0

    # Specific counts of interest
    breakdown_counts = {
        "amount_mismatch_count": predicted_exception_counts.get("amount_mismatch", 0),
        "date_mismatch_count": predicted_exception_counts.get("date_mismatch", 0),
        "status_mismatch_count": predicted_exception_counts.get("status_mismatch", 0),
        "missing_ledger_count": predicted_exception_counts.get("missing_ledger", 0),
        "missing_bank_count": predicted_exception_counts.get("missing_bank", 0),
        "missing_payment_count": predicted_exception_counts.get("missing_payment", 0),
        "unresolved_count": predicted_exception_counts.get("unresolved", 0),
    }

    return {
        "volume": {
            "total_records": total_records,
            "matched": matched_count,
            "exceptions": exception_count,
            "match_rate": match_rate,
            "exception_rate": exception_rate,
        },
        "classification": {
            "correct_classifications": correct_classifications,
            "incorrect_classifications": incorrect_classifications,
            "multiclass_accuracy": multiclass_accuracy,
            "per_class_counts": {
                cls_name: {
                    "expected": data["expected"],
                    "predicted": data["predicted"],
                }
                for cls_name, data in per_class_performance.items()
                if data["expected"] > 0 or data["predicted"] > 0
            },
        },
        "exception_accuracy": {
            "expected_exceptions": dict(expected_exception_counts),
            "predicted_exceptions": dict(predicted_exception_counts),
            "per_class_performance": per_class_performance,
        },
        "binary_metrics": {
            "positive_label": "matched",
            "negative_label": "exception",
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "macro_f1": macro_f1,
        },
        "breakdown": breakdown_counts,
        "performance": {
            "processing_time_seconds": round(elapsed_seconds, 6),
            "throughput_records_per_second": throughput,
        },
    }
