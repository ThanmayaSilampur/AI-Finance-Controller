# AI Finance Controller
### Autonomous Finance Operations Control Center | Razorpay AI Buildathon (Track 04)

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg)](https://www.typescriptlang.org)
[![Tests Passing](https://img.shields.io/badge/tests-108%20passed-success.svg)](#quick-start)

An enterprise finance-ops platform that closes the loop across multi-source records (Payment Gateway, Bank, General Ledger) using a **deterministic 3-way reconciliation engine** paired with an **evidence-grounded AI diagnostic agent**.

---

## Problem

Verification capacity — not generation speed — is the real bottleneck in finance ops. Reconciliation and settlement checks are still done by hand in spreadsheets.

**Our approach:**
- **Deterministic core** — reconciliation and math run on Python `Decimal` precision; LLMs never touch balances or mutate ledger state.
- **Evidence-grounded AI** — LLMs only diagnose isolated exceptions using multi-stream evidence and historical precedents.
- **Human-in-the-loop** — controllers approve, reject, or escalate, backed by an immutable audit trail.

---

## How It Works

1. **Ingest & normalize** CSVs from gateway, bank, and ledger sources.
2. **3-way match** for exact parity, settlement tolerance, and duplicate references (8,500+ rec/s).
3. **Isolate exceptions** — mismatches, missing records, timing delays, duplicates.
4. **AI investigates** flagged exceptions using factual evidence + past precedents.
5. **Human review** with sign-off and audit logging.
6. **Q&A copilot** for natural-language queries on cash position and discrepancies.

---

## Tech Stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic v2, SQLite/PostgreSQL
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **AI:** Gemini / OpenAI (configurable), signature cache, RAG precedent retrieval

---

## Quick Start

```bash
git clone https://github.com/ThanmayaSilampur/AI-Finance-Controller.git
cd AI-Finance-Controller
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GEMINI_API_KEY / OPENAI_API_KEY (optional — mocks by default)
```

**Run:**
```bash
uvicorn app.api:app --reload           # backend → localhost:8000
cd frontend && npm install && npm run dev  # frontend → localhost:5173
```

**Test & benchmark:**
```bash
pytest
python -m app.cli benchmark
```
