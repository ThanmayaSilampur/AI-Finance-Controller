from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class TransactionRecord:
    transaction_id: str
    source_system: str
    amount: Decimal
    currency: str = "INR"
    transaction_date: Optional[date] = None
    status: str = "UNKNOWN"
    reference_id: Optional[str] = None
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def identifier(self) -> str:
        return self.reference_id or self.transaction_id


@dataclass
class ReconciliationResult:
    transaction_id: str
    source_system: str
    matched: bool
    match_score: float
    exception_type: Optional[str] = None
    explanations: List[str] = field(default_factory=list)
    recommended_action: str = "manual_review"
    details: Dict[str, Any] = field(default_factory=dict)
