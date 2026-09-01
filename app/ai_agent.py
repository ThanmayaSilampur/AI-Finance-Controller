from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.audit import AuditStore
from app.db.repository import DatabaseRepository


class AIProvider:
    """Abstract LLM provider interface."""

    def investigate(self, exception: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class MockAIProvider(AIProvider):
    """Deterministic mock provider for tests and local environments without API keys."""

    def investigate(self, exception: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        transaction_id = exception.get("transaction_id") or evidence.get("transaction_id")
        payment_amount = evidence.get("payment_amount")
        bank_amount = evidence.get("bank_amount")
        ledger_amount = evidence.get("ledger_amount")
        difference = evidence.get("difference")
        similar = evidence.get("similar_transactions") or []
        corroborating_records = evidence.get("corroborating_records") or evidence.get("fee_record") or evidence.get("settlement_fee_record")
        known_fee_rule = bool(evidence.get("known_fee_rule"))
        has_strong_support = bool(corroborating_records) or known_fee_rule or (isinstance(similar, list) and len(similar) >= 2)

        if payment_amount is not None and bank_amount is not None and ledger_amount is not None and difference is not None:
            payment_matches_ledger = payment_amount == ledger_amount
            bank_is_lower = bank_amount < payment_amount
            amount_discrepancy_only = payment_matches_ledger and bank_is_lower and difference > 0

            if amount_discrepancy_only and has_strong_support:
                return {
                    "summary": f"Payment and ledger agree at {payment_amount}, while bank settlement is {bank_amount}.",
                    "findings": [
                        "Payment amount matches the ledger amount.",
                        "Bank settlement is lower than the ledger amount.",
                        "The difference aligns with a documented fee pattern.",
                    ],
                    "evidence": [
                        {"source": "payment", "fact": f"Payment = {payment_amount}"},
                        {"source": "ledger", "fact": f"Ledger = {ledger_amount}"},
                        {"source": "bank", "fact": f"Bank = {bank_amount}"},
                        {"source": "historical", "fact": f"Similar transactions observed: {len(similar)} matching cases."},
                    ],
                    "possible_causes": [
                        {
                            "cause": "Possible standard settlement fee.",
                            "likelihood": "HIGH",
                            "reason": "The amount difference matches a recurring fee pattern in similar historical transactions and a known settlement rule.",
                        },
                        {
                            "cause": "Unknown data issue.",
                            "likelihood": "LOW",
                            "reason": "Insufficient evidence to attribute the variance to a specific operational issue.",
                        },
                    ],
                    "most_likely_cause": "Possible standard settlement fee.",
                    "confidence": "HIGH",
                    "recommended_action": "Verify the settlement fee configuration before resolving the exception.",
                    "requires_human_review": True,
                }

        # Insufficient evidence rule
        return {
            "summary": "Insufficient evidence to establish a likely cause.",
            "findings": [
                "A discrepancy exists between payment and bank or ledger data.",
                "Available evidence is not sufficient to assign a reliable explanation.",
            ],
            "evidence": [
                {"source": "transaction", "fact": f"Transaction ID: {transaction_id}"},
            ],
            "possible_causes": [
                {
                    "cause": "UNKNOWN",
                    "likelihood": "LOW",
                    "reason": "Insufficient evidence to support a concrete cause.",
                }
            ],
            "most_likely_cause": "UNKNOWN",
            "confidence": "LOW",
            "recommended_action": "Manual investigation required.",
            "requires_human_review": True,
        }


class OpenAIProvider(AIProvider):
    """Concrete provider wrapper for future LLM integrations."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    def investigate(self, exception: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            return MockAIProvider().investigate(exception, evidence)
        raise NotImplementedError("Live LLM integration is intentionally not implemented in this backend-only stage.")


class InvestigationState:
    PENDING = "PENDING"
    INVESTIGATING = "INVESTIGATING"
    COMPLETED = "COMPLETED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"


class InvestigationStore:
    def __init__(self, path: str | Path = "investigations.json", db: Optional[Session] = None):
        self.db = db
        self.repo = DatabaseRepository(db) if db is not None else None
        self.path = Path(path)
        if self.db is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        if self.repo is not None:
            from app.db.models import InvestigationModel
            models = self.repo.db.query(InvestigationModel).all()
            results = []
            for m in models:
                results.append({
                    "investigation_id": m.investigation_id,
                    "exception_id": m.exception_id,
                    "transaction_id": m.transaction_id,
                    "timestamp": m.created_at.isoformat() if m.created_at else None,
                    "agent_status": m.agent_status,
                    "tools_used": m.tools_used or [],
                    "evidence_collected": m.evidence_collected or {},
                    "findings": m.findings or [],
                    "possible_causes": m.possible_causes or [],
                    "most_likely_cause": m.most_likely_cause,
                    "confidence": m.confidence,
                    "recommendation": m.recommendation,
                    "provider": m.provider,
                    "summary": m.summary,
                    "requires_human_review": m.requires_human_review,
                })
            return results

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _write(self, data: List[Dict[str, Any]]) -> None:
        if self.repo is not None:
            return
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def create_investigation(self, exception_id: str, provider: str, tools_used: List[str], evidence: Dict[str, Any]) -> Dict[str, Any]:
        records = self._read()
        investigation_id = f"INV-{len(records) + 1:03d}"
        transaction_id = str(evidence.get("transaction_id") or "TXN-UNKNOWN")

        if self.repo is not None:
            inv = self.repo.save_investigation(
                investigation_id=investigation_id,
                exception_id=exception_id,
                transaction_id=transaction_id,
                provider=provider,
                agent_status=InvestigationState.PENDING,
                confidence="LOW",
                summary="Investigation initialized.",
                most_likely_cause="UNKNOWN",
                findings=[],
                possible_causes=[],
                evidence_collected=evidence,
                tools_used=tools_used,
                recommendation="Manual investigation required.",
                requires_human_review=True,
            )
            return {
                "investigation_id": inv.investigation_id,
                "exception_id": inv.exception_id,
                "transaction_id": inv.transaction_id,
                "timestamp": inv.created_at.isoformat() if inv.created_at else datetime.now(timezone.utc).isoformat(),
                "agent_status": inv.agent_status,
                "tools_used": inv.tools_used,
                "evidence_collected": inv.evidence_collected,
                "findings": inv.findings,
                "possible_causes": inv.possible_causes,
                "most_likely_cause": inv.most_likely_cause,
                "confidence": inv.confidence,
                "recommendation": inv.recommendation,
                "provider": inv.provider,
                "summary": inv.summary,
                "requires_human_review": inv.requires_human_review,
            }

        record = {
            "investigation_id": investigation_id,
            "exception_id": exception_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_status": InvestigationState.PENDING,
            "tools_used": tools_used,
            "evidence_collected": evidence,
            "findings": [],
            "possible_causes": [],
            "most_likely_cause": "UNKNOWN",
            "confidence": "LOW",
            "recommendation": "Manual investigation required.",
            "provider": provider,
        }
        records.append(record)
        self._write(records)
        return record

    def update_investigation(self, investigation_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if self.repo is not None:
            from app.db.models import InvestigationModel
            inv = self.repo.db.query(InvestigationModel).filter(InvestigationModel.investigation_id == investigation_id).first()
            if not inv:
                raise KeyError(f"No investigation found for {investigation_id}")
            if "agent_status" in updates:
                inv.agent_status = updates["agent_status"]
            if "confidence" in updates:
                inv.confidence = updates["confidence"]
            if "summary" in updates:
                inv.summary = updates["summary"]
            if "most_likely_cause" in updates:
                inv.most_likely_cause = updates["most_likely_cause"]
            if "findings" in updates:
                inv.findings = updates["findings"]
            if "possible_causes" in updates:
                inv.possible_causes = updates["possible_causes"]
            if "evidence_collected" in updates:
                inv.evidence_collected = updates["evidence_collected"]
            if "tools_used" in updates:
                inv.tools_used = updates["tools_used"]
            if "recommendation" in updates:
                inv.recommendation = updates["recommendation"]
            if "requires_human_review" in updates:
                inv.requires_human_review = updates["requires_human_review"]
            self.repo.db.commit()
            return self.get_investigation(investigation_id)

        records = self._read()
        for index, record in enumerate(records):
            if record["investigation_id"] == investigation_id:
                records[index].update(updates)
                self._write(records)
                return records[index]
        raise KeyError(f"No investigation found for {investigation_id}")

    def get_investigation(self, investigation_id: str) -> Dict[str, Any]:
        for record in self._read():
            if record["investigation_id"] == investigation_id:
                return record
        raise KeyError(f"No investigation found for {investigation_id}")


class InvestigationAgent:
    def __init__(self, store: Optional[InvestigationStore] = None, provider: Optional[AIProvider] = None):
        self.store = store or InvestigationStore()
        self.provider = provider or MockAIProvider()

    def get_transaction(self, transaction_id: str, records: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if records is None:
            records = {}
        return {"transaction_id": transaction_id, "records": records}

    def get_related_records(self, transaction_id: str, related: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        return related or []

    def get_exception(self, exception_id: str, exception: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return exception or {"exception_id": exception_id}

    def search_similar_transactions(self, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return criteria.get("similar_transactions", []) if criteria else []

    def get_reconciliation_history(self, transaction_id: str, history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        return history or []

    def investigate_exception(self, exception: Dict[str, Any], evidence: Dict[str, Any], source: str = "mock") -> Dict[str, Any]:
        tools_used = [
            "get_transaction",
            "get_related_records",
            "get_exception",
            "search_similar_transactions",
            "get_reconciliation_history",
        ]
        investigation = self.store.create_investigation(
            exception_id=str(exception.get("exception_id") or exception.get("audit_id") or "EX-UNKNOWN"),
            provider=source,
            tools_used=tools_used,
            evidence=evidence,
        )

        investigation["agent_status"] = InvestigationState.INVESTIGATING
        self.store.update_investigation(investigation["investigation_id"], investigation)

        result = self.provider.investigate(exception, evidence)
        investigation["findings"] = result.get("findings", [])
        investigation["possible_causes"] = result.get("possible_causes", [])
        investigation["most_likely_cause"] = result.get("most_likely_cause", "UNKNOWN")
        investigation["confidence"] = result.get("confidence", "LOW")
        investigation["recommendation"] = result.get("recommended_action", "Manual investigation required.")
        investigation["requires_human_review"] = result.get("requires_human_review", True)
        investigation["agent_status"] = InvestigationState.COMPLETED if result.get("confidence") != "LOW" else InvestigationState.INSUFFICIENT_EVIDENCE
        investigation["summary"] = result.get("summary", "Insufficient evidence.")
        investigation["evidence_collected"] = evidence

        self.store.update_investigation(investigation["investigation_id"], investigation)
        return investigation


def create_default_agent() -> InvestigationAgent:
    return InvestigationAgent(store=InvestigationStore(), provider=MockAIProvider())
