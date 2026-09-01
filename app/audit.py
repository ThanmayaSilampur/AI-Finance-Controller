from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.repository import DatabaseRepository


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
    def __init__(self, path: str | Path = "audit_records.json", db: Optional[Session] = None):
        self.db = db
        self.repo = DatabaseRepository(db) if db is not None else None
        self.path = Path(path)
        if self.db is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        if self.repo is not None:
            from app.db.models import AuditEventModel
            models = self.repo.db.query(AuditEventModel).all()
            results = []
            for m in models:
                exc_id = f"EX-{m.audit_id.split('-')[-1]}"
                res = {
                    "audit_id": m.audit_id,
                    "exception_id": exc_id,
                    "transaction_id": m.transaction_id,
                    "match_status": m.match_status,
                    "exception_type": m.exception_type,
                    "payment_amount": float(m.payment_amount) if m.payment_amount is not None else None,
                    "bank_amount": float(m.bank_amount) if m.bank_amount is not None else None,
                    "ledger_amount": float(m.ledger_amount) if m.ledger_amount is not None else None,
                    "difference": float(m.difference) if m.difference is not None else None,
                    "recommended_action": m.recommended_action,
                    "review_status": m.review_status,
                    "review_history": m.review_history or [],
                    "processing_timestamp": m.processing_timestamp.isoformat() if m.processing_timestamp else None,
                }
                if m.reviewer:
                    res["reviewer"] = m.reviewer
                if m.reviewer_comment:
                    res["reviewer_comment"] = m.reviewer_comment
                if m.resolution_timestamp:
                    res["resolution_timestamp"] = m.resolution_timestamp.isoformat()
                results.append(res)
            return results

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _write(self, data: List[Dict[str, Any]]) -> None:
        if self.repo is not None:
            return
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
        exc_id = f"EX-{len(records) + 1:03d}"

        if self.repo is not None:
            from decimal import Decimal
            event = self.repo.save_audit_event(
                audit_id=audit_id,
                transaction_id=transaction_id,
                match_status=match_status,
                exception_type=exception_type,
                payment_amount=Decimal(str(payment_amount)) if payment_amount is not None else None,
                bank_amount=Decimal(str(bank_amount)) if bank_amount is not None else None,
                ledger_amount=Decimal(str(ledger_amount)) if ledger_amount is not None else None,
                difference=Decimal(str(difference)) if difference is not None else None,
                recommended_action=recommended_action,
                review_status=ReviewState.PENDING.value,
                reviewer=reviewer,
                reviewer_comment=reviewer_comment,
            )
            return {
                "audit_id": event.audit_id,
                "exception_id": exc_id,
                "transaction_id": event.transaction_id,
                "match_status": event.match_status,
                "exception_type": event.exception_type,
                "payment_amount": payment_amount,
                "bank_amount": bank_amount,
                "ledger_amount": ledger_amount,
                "difference": difference,
                "recommended_action": event.recommended_action,
                "review_status": event.review_status,
                "review_history": event.review_history or [],
                "processing_timestamp": event.processing_timestamp.isoformat() if event.processing_timestamp else None,
            }

        record = {
            "audit_id": audit_id,
            "exception_id": exc_id,
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
            if record["audit_id"] == audit_id or record.get("exception_id") == audit_id:
                return record
        raise KeyError(f"No audit record found for {audit_id}")

    def list_pending(self) -> List[Dict[str, Any]]:
        return [record for record in self._read() if record.get("review_status") == ReviewState.PENDING.value]

    def update_record(self, audit_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if self.repo is not None:
            from app.db.models import AuditEventModel
            audit = self.repo.db.query(AuditEventModel).filter(
                (AuditEventModel.audit_id == audit_id) | (AuditEventModel.audit_id == f"AUD-{audit_id.replace('EX-', '')}")
            ).first()
            if not audit:
                raise KeyError(f"No audit record found for {audit_id}")
            if "review_status" in updates:
                audit.review_status = updates["review_status"]
            if "reviewer" in updates:
                audit.reviewer = updates["reviewer"]
            if "reviewer_comment" in updates:
                audit.reviewer_comment = updates["reviewer_comment"]
            if "review_history" in updates:
                audit.review_history = updates["review_history"]
            if "resolution_timestamp" in updates:
                if isinstance(updates["resolution_timestamp"], str):
                    audit.resolution_timestamp = datetime.fromisoformat(updates["resolution_timestamp"])
                else:
                    audit.resolution_timestamp = updates["resolution_timestamp"]
            self.repo.db.commit()
            return self.get_record(audit.audit_id)

        records = self._read()
        for index, record in enumerate(records):
            if record["audit_id"] == audit_id or record.get("exception_id") == audit_id:
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
