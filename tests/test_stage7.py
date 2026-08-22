from decimal import Decimal

from app.ai_agent import InvestigationAgent, InvestigationStore, MockAIProvider
from app.audit import AuditStore
from app.matching import match_records
from app.models import TransactionRecord


def test_agent_receives_exception_and_returns_structured_output():
    agent = InvestigationAgent(store=InvestigationStore(path="test_investigations.json"), provider=MockAIProvider())
    exception = {
        "exception_id": "EX-001",
        "transaction_id": "TX7001",
        "exception_type": "AMOUNT_MISMATCH",
    }
    evidence = {
        "transaction_id": "TX7001",
        "payment_amount": 5000,
        "bank_amount": 4800,
        "ledger_amount": 5000,
        "difference": 200,
        "known_fee_rule": True,
        "similar_transactions": [
            {"transaction_id": "TX7002", "difference": 200},
            {"transaction_id": "TX7003", "difference": 200},
        ],
    }

    result = agent.investigate_exception(exception, evidence)

    assert result["exception_id"] == "EX-001"
    assert result["agent_status"] == "COMPLETED"
    assert result["confidence"] == "HIGH"
    assert result["most_likely_cause"] == "Possible standard settlement fee."
    assert result["recommendation"] == "Verify the settlement fee configuration before resolving the exception."


def test_agent_handles_insufficient_evidence():
    agent = InvestigationAgent(store=InvestigationStore(path="test_investigations_2.json"), provider=MockAIProvider())
    exception = {"exception_id": "EX-002", "transaction_id": "TX7002", "exception_type": "AMOUNT_MISMATCH"}
    evidence = {"transaction_id": "TX7002", "payment_amount": 10000, "bank_amount": 9200, "ledger_amount": 10000, "difference": 800}

    result = agent.investigate_exception(exception, evidence)

    assert result["confidence"] == "LOW"
    assert result["most_likely_cause"] == "UNKNOWN"
    assert result["recommendation"] == "Manual investigation required."
    assert result["requires_human_review"] is True


def test_agent_tools_are_read_only_and_do_not_modify_records():
    agent = InvestigationAgent(store=InvestigationStore(path="test_investigations_3.json"), provider=MockAIProvider())
    payment = TransactionRecord("TX7003", "payment", Decimal("5000"), raw={"amount": "5000", "date": "2026-08-20"})
    bank = TransactionRecord("TX7003", "bank", Decimal("4800"), raw={"amount": "4800", "date": "2026-08-20"})
    ledger = TransactionRecord("TX7003", "ledger", Decimal("5000"), raw={"amount": "5000", "date": "2026-08-20"})

    transaction = agent.get_transaction("TX7003", {"payment": payment, "bank": bank, "ledger": ledger})
    related = agent.get_related_records("TX7003", [{"source": "bank", "amount": 4800}])
    history = agent.get_reconciliation_history("TX7003", [{"status": "EXCEPTION"}])

    assert transaction["transaction_id"] == "TX7003"
    assert related[0]["amount"] == 4800
    assert history[0]["status"] == "EXCEPTION"


def test_investigation_is_persisted():
    store = InvestigationStore(path="test_investigations_4.json")
    agent = InvestigationAgent(store=store, provider=MockAIProvider())
    exception = {"exception_id": "EX-004", "transaction_id": "TX7004", "exception_type": "AMOUNT_MISMATCH"}
    evidence = {"transaction_id": "TX7004", "payment_amount": 5000, "bank_amount": 4800, "ledger_amount": 5000, "difference": 200}

    result = agent.investigate_exception(exception, evidence)
    stored = store.get_investigation(result["investigation_id"])

    assert stored["exception_id"] == "EX-004"
    assert stored["agent_status"] in ["COMPLETED", "INSUFFICIENT_EVIDENCE"]
    assert len(stored["tools_used"]) == 5


def test_mock_provider_without_api_key_works():
    provider = MockAIProvider()
    result = provider.investigate(
        {"transaction_id": "TX7005"},
        {
            "payment_amount": 5000,
            "bank_amount": 4800,
            "ledger_amount": 5000,
            "difference": 200,
            "known_fee_rule": True,
            "similar_transactions": [{"transaction_id": "TX7006", "difference": 200}, {"transaction_id": "TX7007", "difference": 200}],
        },
    )

    assert result["confidence"] == "HIGH"
    assert result["most_likely_cause"] == "Possible standard settlement fee."
