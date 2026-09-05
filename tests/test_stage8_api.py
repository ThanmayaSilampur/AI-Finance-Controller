import json
import urllib.error
import urllib.request

import pytest

from app.api import FinanceAPI


@pytest.fixture()
def api_server(tmp_path):
    data_dir = tmp_path / "api_data"
    api = FinanceAPI(host="127.0.0.1", port=0, data_dir=data_dir)
    api.service.create_analysis_batch(
        payment_content="transaction_id,amount,currency,date,status,customer_id,order_id\nTX001,1000.00,INR,2026-09-01,SUCCESS,C1,O1\nTX002,200.00,INR,2026-09-01,SUCCESS,C2,O2\n",
        bank_content="transaction_id,amount,currency,date,status,bank_name,account_id\nTX001,1000.00,INR,2026-09-01,POSTED,HDFC,A1\nTX002,150.00,INR,2026-09-01,POSTED,HDFC,A1\n",
        ledger_content="transaction_id,amount,currency,date,status,account_code\nTX001,1000.00,INR,2026-09-01,POSTED,AC1\nTX002,200.00,INR,2026-09-01,POSTED,AC1\n",
        batch_name="Test Seed Batch",
    )
    from app.ai_agent import InvestigationAgent, MockAIProvider
    api.service.agent = InvestigationAgent(provider=MockAIProvider())
    api.start()
    base_url = f"http://127.0.0.1:{api.port}"
    try:
        yield base_url
    finally:
        api.stop()


def _request(base_url: str, path: str, method: str = "GET", payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base_url + path, method=method, data=data)
    if data is not None:
        request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read()
            text = body.decode("utf-8")
            content_type = response.headers.get_content_type()
            if content_type == "application/json":
                return response.status, json.loads(text) if text else {}
            return response.status, text
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body) if body else {}
        except json.JSONDecodeError:
            return exc.code, body


def test_health_check(api_server):
    status, payload = _request(api_server, "/health")
    assert status == 200
    assert payload == {"status": "ok"}


def test_get_transactions(api_server):
    status, payload = _request(api_server, "/transactions")
    assert status == 200
    assert isinstance(payload, list)
    assert payload


def test_get_single_transaction(api_server):
    status, transactions = _request(api_server, "/transactions")
    transaction_id = transactions[0]["transaction_id"]
    status, payload = _request(api_server, f"/transactions/{transaction_id}")
    assert status == 200
    assert payload["transaction_id"] == transaction_id
    assert "source_records" in payload


def test_get_missing_transaction(api_server):
    status, payload = _request(api_server, "/transactions/INVALID_TXN")
    assert status == 404
    assert payload["error"] == "TRANSACTION_NOT_FOUND"


def test_get_exceptions(api_server):
    status, payload = _request(api_server, "/exceptions")
    assert status == 200
    assert isinstance(payload, list)
    assert payload


def test_get_single_exception(api_server):
    status, exceptions = _request(api_server, "/exceptions")
    exception_id = exceptions[0]["exception_id"]
    status, payload = _request(api_server, f"/exceptions/{exception_id}")
    assert status == 200
    assert payload["exception_id"] == exception_id
    assert payload["review_status"] == "PENDING"


def test_get_missing_exception(api_server):
    status, payload = _request(api_server, "/exceptions/EX-999")
    assert status == 404
    assert payload["error"] == "EXCEPTION_NOT_FOUND"


def test_investigate_exception(api_server):
    status, exceptions = _request(api_server, "/exceptions")
    exception_id = exceptions[0]["exception_id"]
    status, payload = _request(api_server, f"/exceptions/{exception_id}/investigate", method="POST")
    assert status == 200
    assert payload["exception_id"] == exception_id
    assert payload["investigation_status"] in ["COMPLETED", "INSUFFICIENT_EVIDENCE"]
    assert "confidence" in payload


def test_review_exception(api_server):
    status, exceptions = _request(api_server, "/exceptions")
    exception_id = exceptions[0]["exception_id"]
    status, payload = _request(
        api_server,
        f"/exceptions/{exception_id}/review",
        method="POST",
        payload={"decision": "APPROVED", "reviewer": "finance_admin", "comment": "Confirmed settlement fee."},
    )
    assert status == 200
    assert payload["review_status"] == "APPROVED"


def test_invalid_review_decision(api_server):
    status, exceptions = _request(api_server, "/exceptions")
    exception_id = exceptions[0]["exception_id"]
    status, payload = _request(
        api_server,
        f"/exceptions/{exception_id}/review",
        method="POST",
        payload={"decision": "INVALID", "reviewer": "finance_admin", "comment": "bad"},
    )
    assert status == 400
    assert payload["error"] == "INVALID_REVIEW_DECISION"


def test_invalid_review_transition(api_server):
    status, exceptions = _request(api_server, "/exceptions")
    exception_id = exceptions[0]["exception_id"]
    _request(
        api_server,
        f"/exceptions/{exception_id}/review",
        method="POST",
        payload={"decision": "APPROVED", "reviewer": "finance_admin", "comment": "Already approved."},
    )
    status, payload = _request(
        api_server,
        f"/exceptions/{exception_id}/review",
        method="POST",
        payload={"decision": "APPROVED", "reviewer": "finance_admin", "comment": "Already approved."},
    )
    assert status == 409
    assert payload["error"] == "INVALID_REVIEW_TRANSITION"


def test_get_review_history(api_server):
    status, exceptions = _request(api_server, "/exceptions")
    exception_id = exceptions[0]["exception_id"]
    status, payload = _request(api_server, f"/exceptions/{exception_id}/reviews")
    assert status == 200
    assert isinstance(payload, list)


def test_get_audit_history(api_server):
    status, transactions = _request(api_server, "/transactions")
    transaction_id = transactions[0]["transaction_id"]
    status, payload = _request(api_server, f"/audit/{transaction_id}")
    assert status == 200
    assert payload["transaction_id"] == transaction_id
    assert "audit_records" in payload


def test_get_reconciliation_report(api_server):
    status, payload = _request(api_server, "/reports/reconciliation")
    assert status == 200
    assert "total_records" in payload
    assert "match_rate" in payload


def test_get_exception_report(api_server):
    status, payload = _request(api_server, "/reports/exceptions")
    assert status == 200
    assert "exception_count" in payload
    assert "detailed_exceptions" in payload


def test_export_exception_report_json(api_server):
    status, payload = _request(api_server, "/reports/exceptions/export?format=json")
    assert status == 200
    assert "exception_count" in payload


def test_export_exception_report_csv(api_server):
    status, payload = _request(api_server, "/reports/exceptions/export?format=csv")
    assert status == 200
    assert "transaction_id" in payload


def test_invalid_export_format(api_server):
    status, payload = _request(api_server, "/reports/exceptions/export?format=xml")
    assert status == 422
    assert payload["error"] == "INVALID_FORMAT"


def test_end_to_end_investigation_and_review_flow(api_server):
    status, exceptions = _request(api_server, "/exceptions")
    exception_id = exceptions[0]["exception_id"]
    transaction_id = exceptions[0]["transaction_id"]

    status, investigation = _request(api_server, f"/exceptions/{exception_id}/investigate", method="POST")
    assert status == 200
    assert investigation["exception_id"] == exception_id

    status, refreshed = _request(api_server, f"/exceptions/{exception_id}")
    assert status == 200
    assert refreshed["review_status"] == "PENDING"

    status, review = _request(
        api_server,
        f"/exceptions/{exception_id}/review",
        method="POST",
        payload={"decision": "APPROVED", "reviewer": "finance_admin", "comment": "Confirmed settlement fee."},
    )
    assert status == 200
    assert review["review_status"] == "APPROVED"

    status, updated = _request(api_server, f"/exceptions/{exception_id}")
    assert status == 200
    assert updated["review_status"] == "APPROVED"

    status, history = _request(api_server, f"/exceptions/{exception_id}/reviews")
    assert status == 200
    assert isinstance(history, list)

    status, audit = _request(api_server, f"/audit/{transaction_id}")
    assert status == 200
    assert audit["transaction_id"] == transaction_id
