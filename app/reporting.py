from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Sequence

from app.models import ReconciliationResult


def build_summary(results: Sequence[ReconciliationResult]) -> Dict[str, Any]:
    total_records = len(results)
    matched = sum(1 for result in results if result.matched)
    unresolved = sum(1 for result in results if not result.matched)

    exception_counter = Counter()
    for result in results:
        if result.exception_type:
            exception_counter[result.exception_type] += 1

    match_rate = round((matched / total_records) * 100, 2) if total_records else 0.0

    return {
        "total_records": total_records,
        "matched": matched,
        "unresolved": unresolved,
        "match_rate": match_rate,
        "exception_breakdown": dict(exception_counter),
        "results": [
            {
                "transaction_id": result.transaction_id,
                "matched": result.matched,
                "exception_type": result.exception_type,
                "recommended_action": result.recommended_action,
                "details": result.details,
            }
            for result in results
        ],
    }


def build_exception_report(results: Sequence[ReconciliationResult]) -> Dict[str, Any]:
    summary = build_summary(results)
    exception_count = sum(1 for result in results if result.exception_type)
    resolved_count = sum(1 for result in results if result.exception_type and result.recommended_action == "confirm_and_close")
    unresolved_count = summary["unresolved"]
    total_difference = sum(
        float(item["details"].get("amounts", [0])[0]) if isinstance(item["details"].get("amounts"), list) and item["details"].get("amounts") else 0.0
        for item in summary["results"]
        if item["exception_type"] == "amount_mismatch"
    )

    return {
        "total_records": summary["total_records"],
        "matched_records": summary["matched"],
        "exception_count": exception_count,
        "unresolved_count": unresolved_count,
        "resolved_count": resolved_count,
        "match_rate": summary["match_rate"],
        "resolution_rate": round((resolved_count / max(exception_count, 1)) * 100, 2) if exception_count else 0.0,
        "exception_breakdown": summary["exception_breakdown"],
        "total_financial_difference": round(total_difference, 2),
        "high_value_unresolved_exceptions": [
            entry for entry in summary["results"] if entry["matched"] is False and entry["exception_type"]
        ],
        "detailed_exceptions": summary["results"],
    }


def export_exception_report(results: Sequence[ReconciliationResult], output_path: str | Path, fmt: str = "json") -> str:
    report = build_exception_report(results)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt.lower() == "csv":
        fieldnames = [
            "transaction_id",
            "exception_type",
            "severity",
            "difference",
            "reason",
            "recommended_action",
            "review_status",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow({
                    "transaction_id": result.transaction_id,
                    "exception_type": result.exception_type or "",
                    "severity": "MEDIUM" if result.exception_type else "NONE",
                    "difference": result.details.get("amounts", [""])[0] if result.exception_type == "amount_mismatch" else "",
                    "reason": result.explanations[0] if result.explanations else "",
                    "recommended_action": result.recommended_action,
                    "review_status": "PENDING" if not result.matched else "RESOLVED",
                })
    else:
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return str(path)
