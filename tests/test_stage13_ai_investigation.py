from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.ai_agent import InvestigationAgent, InvestigationState, InvestigationStore, MockAIProvider
from app.audit import AuditStore, ReviewState, transition_review_state
from app.api import FinanceAPI
from app.db.models import ExceptionModel
from app.db.repository import DatabaseRepository
from app.db.testing import create_all_tables
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test_stage13.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    create_all_tables(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_amount_mismatch_investigation():
    """A. Amount mismatch: exact actual amounts, Decimal difference, evidence present, no unsupported causal claim."""
    provider = MockAIProvider()
    exception = {
        "exception_id": "EX-101",
        "transaction_id": "TX-101",
        "exception_type": "amount_mismatch",
    }
    evidence = {
        "transaction_id": "TX-101",
        "payment_amount": Decimal("5000.00"),
        "bank_amount": Decimal("4850.00"),
        "ledger_amount": Decimal("5000.00"),
        "difference": Decimal("150.00"),
        "legs_present": ["payment", "bank", "ledger"],
        "missing_legs": [],
    }

    result = provider.investigate(exception, evidence)

    assert result["exception_id"] == "EX-101"
    assert result["exception_type"] == "amount_mismatch"
    assert result["confidence"] == "HIGH"
    assert "150.00" in result["diagnosis"]
    assert result["recommended_action"] == "REVIEW"
    assert "limitations" in result
    assert len(result["limitations"]) > 0
    # Verify no fabricated definitive claim
    assert "Possible" in result["likely_cause"] or "variance" in result["likely_cause"].lower()


def test_date_mismatch_investigation():
    """B. Date mismatch: differing dates correctly reported, cause treated as inference."""
    provider = MockAIProvider()
    exception = {
        "exception_id": "EX-102",
        "transaction_id": "TX-102",
        "exception_type": "date_mismatch",
    }
    evidence = {
        "transaction_id": "TX-102",
        "payment_date": "2026-08-10",
        "bank_date": "2026-08-11",
        "ledger_date": "2026-08-10",
        "legs_present": ["payment", "bank", "ledger"],
        "missing_legs": [],
    }

    result = provider.investigate(exception, evidence)

    assert result["confidence"] == "HIGH"
    assert "2026-08-10" in result["diagnosis"]
    assert "2026-08-11" in result["diagnosis"]
    assert "Possible" in result["likely_cause"] or "delay" in result["likely_cause"].lower()
    assert result["recommended_action"] == "REVIEW"
    assert any("not establish" in lim for lim in result["limitations"])


def test_status_mismatch_investigation():
    """C. Status mismatch: statuses correctly reported by stream, cause as inference."""
    provider = MockAIProvider()
    exception = {
        "exception_id": "EX-103",
        "transaction_id": "TX-103",
        "exception_type": "status_mismatch",
    }
    evidence = {
        "transaction_id": "TX-103",
        "payment_status": "SUCCESS",
        "bank_status": "SUCCESS",
        "ledger_status": "PENDING",
        "legs_present": ["payment", "bank", "ledger"],
        "missing_legs": [],
    }

    result = provider.investigate(exception, evidence)

    assert result["confidence"] == "HIGH"
    assert "PENDING" in result["diagnosis"]
    assert "SUCCESS" in result["diagnosis"]
    assert result["recommended_action"] == "REVIEW"
    assert any("divergence" in lim or "gateway" in lim for lim in result["limitations"])


def test_missing_ledger_investigation():
    """D. Missing ledger: explicitly represented, no fabricated ledger record."""
    provider = MockAIProvider()
    exception = {
        "exception_id": "EX-104",
        "transaction_id": "TX-104",
        "exception_type": "missing_ledger",
    }
    evidence = {
        "transaction_id": "TX-104",
        "payment_amount": Decimal("1500.00"),
        "bank_amount": Decimal("1500.00"),
        "ledger_amount": None,
        "legs_present": ["payment", "bank"],
        "missing_legs": ["ledger"],
    }

    result = provider.investigate(exception, evidence)

    assert result["confidence"] == "HIGH"
    assert "no corresponding ledger entry was found" in result["diagnosis"].lower()
    assert result["recommended_action"] == "REVIEW"
    assert any("ledger" in s for s in result["evidence"])
    assert any("Missing record stream: ledger" == s for s in result["evidence"])


def test_missing_bank_investigation():
    """E. Missing bank: explicitly represented, no fabricated bank record."""
    provider = MockAIProvider()
    exception = {
        "exception_id": "EX-105",
        "transaction_id": "TX-105",
        "exception_type": "missing_bank",
    }
    evidence = {
        "transaction_id": "TX-105",
        "payment_amount": Decimal("2000.00"),
        "ledger_amount": Decimal("2000.00"),
        "bank_amount": None,
        "legs_present": ["payment", "ledger"],
        "missing_legs": ["bank"],
    }

    result = provider.investigate(exception, evidence)

    assert result["confidence"] == "HIGH"
    assert "bank statement" in result["diagnosis"].lower()
    assert result["recommended_action"] == "REVIEW"
    assert any("Missing record stream: bank" == s for s in result["evidence"])


def test_missing_payment_investigation():
    """F. Missing payment: explicitly represented, no fabricated payment record."""
    provider = MockAIProvider()
    exception = {
        "exception_id": "EX-106",
        "transaction_id": "TX-106",
        "exception_type": "missing_payment",
    }
    evidence = {
        "transaction_id": "TX-106",
        "bank_amount": Decimal("3500.00"),
        "ledger_amount": Decimal("3500.00"),
        "payment_amount": None,
        "legs_present": ["bank", "ledger"],
        "missing_legs": ["payment"],
    }

    result = provider.investigate(exception, evidence)

    assert result["confidence"] == "HIGH"
    assert "payment record was found" in result["diagnosis"].lower()
    assert result["recommended_action"] == "REVIEW"
    assert any("Missing record stream: payment" == s for s in result["evidence"])


def test_unresolved_insufficient_evidence():
    """G. Unresolved: LOW confidence, explicit limitations, recommended action ESCALATE."""
    provider = MockAIProvider()
    exception = {
        "exception_id": "EX-107",
        "transaction_id": "TX-107",
        "exception_type": "unresolved",
    }
    evidence = {
        "transaction_id": "TX-107",
        "payment_amount": Decimal("900.00"),
        "legs_present": ["payment"],
        "missing_legs": ["bank", "ledger"],
    }

    result = provider.investigate(exception, evidence)

    assert result["confidence"] == "LOW"
    assert result["recommended_action"] in ("REVIEW", "ESCALATE")
    assert len(result["limitations"]) > 0
    assert any("insufficient" in lim.lower() for lim in result["limitations"])


def test_ground_truth_isolation():
    """H. Ground-truth isolation: AI investigation never receives benchmark ground truth."""
    agent = InvestigationAgent(provider=MockAIProvider())
    exception = {"exception_id": "EX-108", "transaction_id": "TX-108", "exception_type": "amount_mismatch"}
    evidence = {
        "transaction_id": "TX-108",
        "payment_amount": Decimal("1000.00"),
        "bank_amount": Decimal("950.00"),
        "ledger_amount": Decimal("1000.00"),
        "legs_present": ["payment", "bank", "ledger"],
        "missing_legs": [],
    }

    # Verify that passing only factual transaction fields functions cleanly without any benchmark file or ground truth
    investigation = agent.investigate_exception(exception, evidence)
    assert "benchmark" not in investigation
    assert "ground_truth" not in investigation
    assert investigation["confidence"] == "HIGH"


def test_human_review_workflow(tmp_path):
    """I. Human review: review persists, correct state transition, human authoritative."""
    store = AuditStore(str(tmp_path / "audit_review.json"))
    rec = store.create_record(
        transaction_id="TX-REV-1",
        match_status="EXCEPTION",
        exception_type="amount_mismatch",
        payment_amount=5000.0,
        bank_amount=4800.0,
        difference=200.0,
    )
    assert rec["review_status"] == ReviewState.PENDING.value

    # Approve
    approved = transition_review_state(store, rec["audit_id"], ReviewState.APPROVED, "reviewer_1", "Fee confirmed.")
    assert approved["review_status"] == ReviewState.APPROVED.value
    assert len(approved["review_history"]) == 1
    assert approved["review_history"][0]["previous_state"] == "PENDING"
    assert approved["review_history"][0]["new_state"] == "APPROVED"

    # Escalate from approved
    escalated = transition_review_state(store, rec["audit_id"], ReviewState.ESCALATED, "reviewer_2", "Reopened for re-audit.")
    assert escalated["review_status"] == ReviewState.ESCALATED.value
    assert len(escalated["review_history"]) == 2


def test_audit_no_duplicate_history(db_session):
    """J. Audit: no duplicate history entries when updating via repo/store."""
    repo = DatabaseRepository(db_session)
    exc = repo.save_exception(
        exception_id="EX-AUD-1",
        audit_id="AUD-AUD-1",
        transaction_id="TX-AUD-1",
        exception_type="amount_mismatch",
        recommended_action="REVIEW",
    )
    repo.save_audit_event(
        audit_id="AUD-AUD-1",
        transaction_id="TX-AUD-1",
        match_status="EXCEPTION",
        exception_type="amount_mismatch",
    )

    review = repo.add_review(
        exception_id="EX-AUD-1",
        previous_state="PENDING",
        new_state="APPROVED",
        reviewer="lead_auditor",
        comment="Verified.",
    )
    assert review.new_state == "APPROVED"

    reviews = repo.list_reviews("EX-AUD-1")
    assert len(reviews) == 1


def test_api_end_to_end(tmp_path):
    """K. API End-to-End: investigate, get result, review, audit history."""
    import urllib.request
    from app.ai_agent import InvestigationAgent, MockAIProvider

    data_dir = tmp_path / "api_data_stage13"
    api = FinanceAPI(host="127.0.0.1", port=0, data_dir=data_dir)
    api.service.create_analysis_batch(
        payment_content="transaction_id,amount,currency,date,status,customer_id,order_id\nTX001,1000.00,INR,2026-09-01,SUCCESS,C1,O1\nTX002,200.00,INR,2026-09-01,SUCCESS,C2,O2\n",
        bank_content="transaction_id,amount,currency,date,status,bank_name,account_id\nTX001,1000.00,INR,2026-09-01,POSTED,HDFC,A1\nTX002,150.00,INR,2026-09-01,POSTED,HDFC,A1\n",
        ledger_content="transaction_id,amount,currency,date,status,account_code\nTX001,1000.00,INR,2026-09-01,POSTED,AC1\nTX002,200.00,INR,2026-09-01,POSTED,AC1\n",
        batch_name="Test Seed Batch",
    )
    api.service.agent = InvestigationAgent(store=api.service.investigation_store, provider=MockAIProvider())
    api.start()
    base_url = f"http://127.0.0.1:{api.port}"

    try:
        # 1. Fetch exceptions
        req = urllib.request.Request(f"{base_url}/exceptions")
        with urllib.request.urlopen(req) as resp:
            exceptions = json.loads(resp.read().decode("utf-8"))
        assert len(exceptions) > 0
        exc = exceptions[0]
        exc_id = exc["exception_id"]

        # 2. Trigger AI Investigation
        req = urllib.request.Request(f"{base_url}/exceptions/{exc_id}/investigate", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            inv = json.loads(resp.read().decode("utf-8"))

        assert inv["exception_id"] == exc_id
        assert inv["investigation_status"] in ("COMPLETED", "INSUFFICIENT_EVIDENCE")
        assert inv["confidence"] in ("HIGH", "MEDIUM", "LOW")
        assert "diagnosis" in inv
        assert "likely_cause" in inv
        assert "recommended_action" in inv
        assert "evidence" in inv

        # 3. Perform Human Review
        review_payload = json.dumps({
            "decision": "APPROVED",
            "reviewer": "chief_risk_officer",
            "comment": "Approved following AI evidence analysis.",
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/exceptions/{exc_id}/review", data=review_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            rev_res = json.loads(resp.read().decode("utf-8"))
        assert rev_res["review_status"] == "APPROVED"

        # 4. Review History
        req = urllib.request.Request(f"{base_url}/exceptions/{exc_id}/reviews")
        with urllib.request.urlopen(req) as resp:
            rev_history = json.loads(resp.read().decode("utf-8"))
        assert len(rev_history) >= 1
        assert rev_history[-1]["new_state"] == "APPROVED"

        # 5. Audit History
        tx_id = exc["transaction_id"]
        req = urllib.request.Request(f"{base_url}/audit/{tx_id}")
        with urllib.request.urlopen(req) as resp:
            audit = json.loads(resp.read().decode("utf-8"))
        assert audit["transaction_id"] == tx_id
        assert len(audit["investigations"]) >= 1

    finally:
        api.stop()
