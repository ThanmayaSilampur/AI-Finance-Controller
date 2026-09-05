from __future__ import annotations

import pytest
from app.ai_agent import (
    AIConfigurationError,
    FinanceCopilotAgent,
    MockAIProvider,
    RealLLMProvider,
)
from app.api import FinanceService, app


DATASET_PAYMENT = """transaction_id,amount,currency,date,status,customer_id,order_id
TX001,1000.00,INR,2026-09-01,SUCCESS,C1,O1
TX002,200.00,INR,2026-09-01,SUCCESS,C2,O2
"""

DATASET_BANK = """transaction_id,amount,currency,date,status,bank_name,account_id
TX001,1000.00,INR,2026-09-01,POSTED,HDFC,A1
TX002,150.00,INR,2026-09-01,POSTED,HDFC,A1
"""

DATASET_LEDGER = """transaction_id,amount,currency,date,status,account_code
TX001,1000.00,INR,2026-09-01,POSTED,AC1
TX002,200.00,INR,2026-09-01,POSTED,AC1
"""


def test_copilot_agent_with_mock_provider():
    mock_provider = MockAIProvider()
    copilot = FinanceCopilotAgent(provider=mock_provider)

    batch_context = {
        "batch_id": "BATCH-TEST-001",
        "batch_name": "Test Run",
        "total_records": 2,
        "matched_count": 1,
        "exception_count": 1,
        "match_rate": 50.0,
        "net_variance": 50.0,
        "exception_breakdown": {"amount_mismatch": 1},
    }
    tx_evidence = [
        {
            "transaction_id": "TX002",
            "source_records": {
                "payment": {"amount": "200.00"},
                "bank": {"amount": "150.00"},
                "ledger": {"amount": "200.00"},
            },
        }
    ]

    res = copilot.answer_query(
        query="Why did TX002 fail to match?",
        batch_context=batch_context,
        transaction_evidence=tx_evidence,
    )

    assert res["query"] == "Why did TX002 fail to match?"
    assert res["batch_id"] == "BATCH-TEST-001"
    assert "TX002" in res["referenced_transactions"]
    assert "Deterministic Copilot Advisory" in res["answer"]


def test_copilot_service_grounding(tmp_path):
    data_dir = tmp_path / "copilot_data"
    service = FinanceService(data_dir=data_dir, seed_on_empty=False)
    service.agent.provider = MockAIProvider()

    batch = service.create_analysis_batch(
        payment_content=DATASET_PAYMENT,
        bank_content=DATASET_BANK,
        ledger_content=DATASET_LEDGER,
        batch_name="Copilot Batch A",
    )

    res = service.answer_copilot_query(
        query="What is the overall match rate for this batch?",
        batch_id=batch["batch_id"],
    )

    assert res["batch_id"] == batch["batch_id"]
    assert "answer" in res
    assert "timestamp" in res


def test_copilot_unconfigured_error(tmp_path):
    data_dir = tmp_path / "copilot_unconf"
    service = FinanceService(data_dir=data_dir, seed_on_empty=False)

    unconf_provider = RealLLMProvider()
    unconf_provider._active_provider = None
    unconf_provider.provider_name = "EXPLICITLY_UNCONFIGURED"
    service.agent.provider = unconf_provider

    with pytest.raises(AIConfigurationError):
        service.answer_copilot_query("Any question?")


def test_copilot_api_endpoint(monkeypatch, tmp_path):
    import app.api as api_mod
    data_dir = tmp_path / "copilot_api_data"
    test_service = FinanceService(data_dir=data_dir, seed_on_empty=False)
    test_service.agent.provider = MockAIProvider()
    monkeypatch.setattr(api_mod, "service", test_service)

    batch = test_service.create_analysis_batch(
        payment_content=DATASET_PAYMENT,
        bank_content=DATASET_BANK,
        ledger_content=DATASET_LEDGER,
        batch_name="API Copilot Batch",
    )

    req = api_mod.CopilotQueryRequest(
        query="Tell me about transaction TX002 and variance",
        batch_id=batch["batch_id"],
    )
    data = api_mod.copilot_query(req)

    assert "answer" in data
    assert data["batch_id"] == batch["batch_id"]
    assert "TX002" in data["referenced_transactions"]
