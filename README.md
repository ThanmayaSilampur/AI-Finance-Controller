# AI Finance Controller Backend

The AI Finance Controller reconciles payment, bank, and ledger records with deterministic matching, audit history, human review workflows, reporting, and a read-only investigation agent. It is currently a backend-only service; no frontend is included.

## Architecture

- `app/ingestion.py` loads source records.
- `app/normalization.py` canonicalizes amounts, dates, and statuses.
- `app/matching.py` performs deterministic reconciliation.
- `app/reporting.py` builds summaries and exception exports.
- `app/audit.py` persists review state and history.
- `app/ai_agent.py` provides the investigation abstraction.
- `app/api.py` exposes the existing services through FastAPI and a compatibility HTTP server.

Production persistence remains local JSON storage. Set `FINANCE_DATA_DIR` to select its directory; the default is the repository `data/` directory.

## Tech stack

- Python 3.13
- FastAPI and Uvicorn
- Pydantic
- pytest
- JSON persistence for audit and investigation records

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

## Local setup

Create and activate a Python 3.13 virtual environment, then install the pinned dependencies:

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Keep `.env`, virtual environments, caches, generated data, and test artifacts outside commits. The repository `.gitignore` already excludes them.

## Run tests

```powershell
.\.venv313\Scripts\python.exe -m pytest -q
```

## Start the API

```powershell
.\.venv313\Scripts\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

For deployment, use `--host 0.0.0.0`. The health endpoint is `GET http://localhost:8000/health` and returns `{"status":"ok"}`.

The API also provides transaction, exception, review, audit, reconciliation-report, exception-report, and JSON/CSV export endpoints. See the route definitions in `app/api.py` for the complete contract.

## Docker

Build and run the API from the repository root:

```powershell
docker build -t ai-finance-controller .
docker run --rm -p 8000:8000 ai-finance-controller
```

To keep JSON persistence in a host directory, set `FINANCE_DATA_DIR` and mount that directory into the container:

```powershell
docker run --rm -p 8000:8000 -e FINANCE_DATA_DIR=/app/data -v ${PWD}/data:/app/data ai-finance-controller
```

The image uses Python 3.13, installs from `requirements.txt`, and starts Uvicorn on port 8000. `.dockerignore` prevents local environments, secrets, caches, and generated data from entering the image.

## CI/CD

`.github/workflows/ci.yml` runs on pushes and pull requests. It uses Python 3.13, installs `requirements.txt`, and runs the complete pytest suite. A failing test causes the workflow to fail. Deployment is not automated yet.

## Current limitations

- Persistence is file-based JSON and is not designed for concurrent multi-instance production writes.
- The investigation provider is currently a deterministic mock provider.
- Input ingestion is file-oriented rather than a production queue or database integration.
- The existing date normalization path emits a Python deprecation warning for date strings without a year.
- No frontend, authentication, authorization, or automated deployment target is included.

## Important safety boundary

The AI investigation endpoint is read-only and never approves, rejects, or mutates financial records. Only the explicit human review endpoint may change review state.
