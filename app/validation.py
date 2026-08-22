from __future__ import annotations

from decimal import Decimal
from typing import Dict, List


def generate_synthetic_batch(size: int = 60) -> Dict[str, List[dict]]:
    """Create a synthetic financial batch with a mix of matched and mismatched records."""
    payment = []
    bank = []
    ledger = []

    for index in range(1, size + 1):
        txn_id = f"TX{index:04d}"
        amount = Decimal(str(1000 + (index * 37) % 9000))
        date = f"2026-08-{(index % 28) + 1:02d}"

        payment_row = {
            "transaction_id": txn_id,
            "reference_id": f"REF{index:04d}",
            "amount": str(amount),
            "date": date,
            "status": "SUCCESS" if index % 4 != 0 else "FAILED",
            "customer_id": f"CUST{index:04d}",
            "order_id": f"ORD{index:04d}",
        }
        bank_row = {
            "transaction_id": txn_id,
            "reference_id": f"REF{index:04d}",
            "amount": str(amount),
            "date": date,
            "status": "POSTED" if index % 6 != 0 else "REVERSED",
            "customer_id": f"CUST{index:04d}",
            "order_id": f"ORD{index:04d}",
        }
        ledger_row = {
            "transaction_id": txn_id,
            "reference_id": f"REF{index:04d}",
            "amount": str(amount) if index % 5 != 0 else str(amount - Decimal("500")),
            "date": date if index % 7 != 0 else f"2026-08-{(index % 28) + 2:02d}",
            "status": "PAID" if index % 3 != 0 else "PENDING",
            "customer_id": f"CUST{index:04d}",
            "order_id": f"ORD{index:04d}",
        }

        payment.append(payment_row)
        bank.append(bank_row)
        ledger.append(ledger_row)

    return {"payment": payment, "bank": bank, "ledger": ledger}
