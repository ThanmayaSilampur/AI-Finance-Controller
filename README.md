# Finance Controller Backend

This project contains the deterministic finance reconciliation backend with audit review and AI investigation support.

## API

The backend exposes a lightweight REST API built with FastAPI. The API is intentionally backend-only and does not add any frontend or dashboard UI.

### Health

- GET /health

### Transactions

- GET /transactions
- GET /transactions/{transaction_id}

### Exceptions and review

- GET /exceptions
- GET /exceptions/{exception_id}
- POST /exceptions/{exception_id}/investigate
- POST /exceptions/{exception_id}/review
- GET /exceptions/{exception_id}/reviews

### Audit and reporting

- GET /audit/{transaction_id}
- GET /reports/reconciliation
- GET /reports/exceptions
- GET /reports/exceptions/export?format=json
- GET /reports/exceptions/export?format=csv

### Example

```bash
curl http://localhost:8000/health
curl http://localhost:8000/transactions
curl -X POST http://localhost:8000/exceptions/EX-001/investigate
curl -X POST http://localhost:8000/exceptions/EX-001/review -H "Content-Type: application/json" -d '{"decision":"APPROVED","reviewer":"finance_admin","comment":"Confirmed settlement fee."}'
```

## Running locally

```bash
cd c:/Users/silam/OneDrive/Desktop/razorpay
c:/Users/silam/OneDrive/Desktop/razorpay/.venv/Scripts/python.exe -m uvicorn app.api:app --reload
```

## Important safety boundary

The AI investigation endpoint is read-only and never approves, rejects, or mutates financial records. Only the explicit human review endpoint may change review state.
