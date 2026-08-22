from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ReviewState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"

    @classmethod
    def allowed_transitions(cls, current: str) -> List[str]:
        if current == cls.PENDING.value:
            return [cls.APPROVED.value, cls.REJECTED.value, cls.ESCALATED.value]
        if current in [cls.APPROVED.value, cls.REJECTED.value, cls.ESCALATED.value]:
            return [cls.ESCALATED.value]
        return []


class AuditStore:
    def __init__(self, path: str | Path = "audit_records.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _write(self, data: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def create_record(
        self,
        transaction_id: str,
        match_status: str,
        exception_type: str,
        payment_amount: Optional[float] = None,
        bank_amount: Optional[float] = None,
        ledger_amount: Optional[float] = None,
        difference: Optional[float] = None,
        recommended_action: str = "MANUAL_REVIEW",
        reviewer: Optional[str] = None,
        reviewer_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        records = self._read()
        audit_id = f"AUD-{len(records) + 1:03d}"
        record = {
            "audit_id": audit_id,
            "transaction_id": transaction_id,
            "match_status": match_status,
            "exception_type": exception_type,
            "payment_amount": payment_amount,
            "bank_amount": bank_amount,
            "ledger_amount": ledger_amount,
            "difference": difference,
            "recommended_action": recommended_action,
            "review_status": ReviewState.PENDING.value,
            "review_history": [],
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if reviewer:
            record["reviewer"] = reviewer
        if reviewer_comment:
            record["reviewer_comment"] = reviewer_comment
        records.append(record)
        self._write(records)
        return record

    def get_record(self, audit_id: str) -> Dict[str, Any]:
        for record in self._read():
            if record["audit_id"] == audit_id:
                return record
        raise KeyError(f"No audit record found for {audit_id}")

    def list_pending(self) -> List[Dict[str, Any]]:
        return [record for record in self._read() if record.get("review_status") == ReviewState.PENDING.value]

    def update_record(self, audit_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        records = self._read()
        for index, record in enumerate(records):
            if record["audit_id"] == audit_id:
                records[index].update(updates)
                self._write(records)
                return records[index]
        raise KeyError(f"No audit record found for {audit_id}")


def transition_review_state(store: AuditStore, audit_id: str, new_state: ReviewState, reviewer: str, comment: str) -> Dict[str, Any]:
    record = store.get_record(audit_id)
    previous_state = record.get("review_status", ReviewState.PENDING.value)
    allowed = ReviewState.allowed_transitions(previous_state)
    if new_state.value not in allowed:
        raise ValueError(f"Invalid transition from {previous_state} to {new_state.value}")

    history_entry = {
        "previous_state": previous_state,
        "new_state": new_state.value,
        "reviewer": reviewer,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "comment": comment,
    }
    record.setdefault("review_history", []).append(history_entry)
    record["review_status"] = new_state.value
    record["reviewer"] = reviewer
    record["reviewer_comment"] = comment
    record["resolution_timestamp"] = datetime.now(timezone.utc).isoformat()
    return store.update_record(audit_id, record)


def list_pending_exceptions(store: AuditStore) -> List[Dict[str, Any]]:
    return store.list_pending()


def get_exception_details(store: AuditStore, audit_id: str) -> Dict[str, Any]:
    return store.get_record(audit_id)


def approve_exception(store: AuditStore, audit_id: str, reviewer: str, comment: str) -> Dict[str, Any]:
    return transition_review_state(store, audit_id, ReviewState.APPROVED, reviewer, comment)


def reject_exception(store: AuditStore, audit_id: str, reviewer: str, comment: str) -> Dict[str, Any]:
    return transition_review_state(store, audit_id, ReviewState.REJECTED, reviewer, comment)


def escalate_exception(store: AuditStore, audit_id: str, reviewer: str, comment: str) -> Dict[str, Any]:
    return transition_review_state(store, audit_id, ReviewState.ESCALATED, reviewer, comment)


def detect_duplicate_transaction(records: List[Any]) -> bool:
    seen = set()
    for record in records:
        key = str(getattr(record, "transaction_id", ""))
        if key in seen:
            return True
        seen.add(key)
    return False


def detect_fee_difference(payment_amount: float | int | str | None, settlement_amount: float | int | str | None) -> bool:
    try:
        payment = float(payment_amount)
        settlement = float(settlement_amount)
    except (TypeError, ValueError):
        return False
    return payment > 0 and settlement > 0 and payment - settlement > 0 and (payment - settlement) <= payment * 0.2


def build_exception_explanation(expected: str, observed: str, difference: str, evidence: str, likely_reason: str, recommended_action: str) -> Dict[str, str]:
    return {
        "expected": expected,
        "observed": observed,
        "difference": difference,
        "evidence": evidence,
        "likely_reason": likely_reason,
        "recommended_action": recommended_action,
    }
