from __future__ import annotations

import csv
import io
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker

from app.ai_agent import (
    AIConfigurationError,
    AIProviderError,
    FinanceCopilotAgent,
    InvestigationAgent,
    InvestigationStore,
    RealLLMProvider,
)
from app.audit import AuditStore, ReviewState, transition_review_state
from app.db.adapter import DataAdapter
from app.db.models import (
    AnalysisBatchModel,
    AuditEventModel,
    BankRecordModel,
    ExceptionModel,
    InvestigationModel,
    LedgerRecordModel,
    PaymentRecordModel,
    ReviewModel,
    TransactionModel,
)
from app.db.repository import DatabaseRepository
from app.db.session import SessionFactory, create_db_engine
from app.db.migration import run_migrations
from app.ingestion import parse_csv_records
from app.matching import match_records
from app.models import ReconciliationResult, TransactionRecord
from app.normalization import normalize_records
from app.reporting import build_exception_report, build_summary, export_exception_report as export_exception_report_helper


class FinanceService:
    def __init__(
        self,
        data_dir: Optional[str | Path] = None,
        database_url: Optional[str] = None,
        seed_on_empty: bool = False,
    ) -> None:
        default_data_dir = Path(__file__).resolve().parent.parent / "data"
        if data_dir is not None:
            candidate_dir = Path(data_dir)
            try:
                candidate_dir.mkdir(parents=True, exist_ok=True)
                self.data_dir = candidate_dir
            except (PermissionError, OSError):
                default_data_dir.mkdir(parents=True, exist_ok=True)
                self.data_dir = default_data_dir
        else:
            default_data_dir.mkdir(parents=True, exist_ok=True)
            self.data_dir = default_data_dir

        # Initialize Database engine & session
        if database_url:
            self.engine = create_db_engine(database_url)
        elif data_dir is not None:
            db_path = self.data_dir / "finance_controller.db"
            self.engine = create_db_engine(f"sqlite:///{db_path}")
        else:
            self.engine = create_db_engine()

        _db_url = (
            database_url
            if database_url
            else (f"sqlite:///{self.data_dir / 'finance_controller.db'}" if data_dir is not None else None)
        )
        run_migrations(_db_url or self.engine.url.render_as_string(hide_password=False))

        self.session_factory = sessionmaker(bind=self.engine)

        self.db = self.session_factory()
        self.repo = DatabaseRepository(self.db)

        self.audit_store = AuditStore(path=self.data_dir / "audit_records.json", db=self.db)
        self.investigation_store = InvestigationStore(path=self.data_dir / "investigations.json", db=self.db)
        self.agent = InvestigationAgent(store=self.investigation_store, provider=RealLLMProvider())

        self.active_batch_id: Optional[str] = None
        self.results: List[ReconciliationResult] = []
        self.payment_records: List[TransactionRecord] = []
        self.bank_records: List[TransactionRecord] = []
        self.ledger_records: List[TransactionRecord] = []

        batches = self.repo.list_analysis_batches()
        if batches:
            self.active_batch_id = batches[0].batch_id
            self._reload_batch(self.active_batch_id)

    def _reload_batch(self, batch_id: Optional[str]) -> None:
        if not batch_id:
            self.results = []
            self.payment_records = []
            self.bank_records = []
            self.ledger_records = []
            return

        query_p = self.db.query(PaymentRecordModel).filter(PaymentRecordModel.batch_id == batch_id)
        query_b = self.db.query(BankRecordModel).filter(BankRecordModel.batch_id == batch_id)
        query_l = self.db.query(LedgerRecordModel).filter(LedgerRecordModel.batch_id == batch_id)

        payments = [
            TransactionRecord(
                transaction_id=p.transaction_id,
                source_system="payment",
                amount=p.amount,
                currency=p.currency,
                transaction_date=p.transaction_date,
                status=p.status,
                reference_id=p.reference_id,
                customer_id=p.customer_id,
                order_id=p.order_id,
                raw=p.raw_payload or {},
            )
            for p in query_p.all()
        ]
        banks = [
            TransactionRecord(
                transaction_id=b.transaction_id,
                source_system="bank",
                amount=b.amount,
                currency=b.currency,
                transaction_date=b.transaction_date,
                status=b.status,
                reference_id=b.reference_id,
                raw=b.raw_payload or {},
            )
            for b in query_b.all()
        ]
        ledgers = [
            TransactionRecord(
                transaction_id=l.transaction_id,
                source_system="ledger",
                amount=l.amount,
                currency=l.currency,
                transaction_date=l.transaction_date,
                status=l.status,
                reference_id=l.reference_id,
                raw=l.raw_payload or {},
            )
            for l in query_l.all()
        ]

        self.payment_records = payments
        self.bank_records = banks
        self.ledger_records = ledgers
        self.results = match_records(payments, banks, ledgers) if (payments or banks or ledgers) else []

    def _reload_reconciliation_results(self) -> None:
        self._reload_batch(self.active_batch_id)

    def _build_records(self, rows: List[dict], source_system: str) -> List[TransactionRecord]:
        records: List[TransactionRecord] = []
        for row in rows:
            records.append(
                TransactionRecord(
                    transaction_id=str(row.get("transaction_id") or row.get("id") or "UNKNOWN"),
                    source_system=source_system,
                    amount=Decimal("0"),
                    raw=dict(row),
                )
            )
        return normalize_records(records)

    def _build_exception_record_for_records(
        self,
        result: Any,
        payments: List[TransactionRecord],
        banks: List[TransactionRecord],
        ledgers: List[TransactionRecord],
    ) -> Dict[str, Any]:
        payment = next((item for item in payments if item.transaction_id == result.transaction_id), None)
        bank = next((item for item in banks if item.transaction_id == result.transaction_id), None)
        ledger = next((item for item in ledgers if item.transaction_id == result.transaction_id), None)
        payment_amount = payment.amount if payment else None
        bank_amount = bank.amount if bank else None
        ledger_amount = ledger.amount if ledger else None
        difference: Optional[Decimal] = None
        if payment_amount is not None and bank_amount is not None:
            difference = abs(payment_amount - bank_amount)
        elif payment_amount is not None and ledger_amount is not None:
            difference = abs(payment_amount - ledger_amount)
        elif bank_amount is not None and ledger_amount is not None:
            difference = abs(bank_amount - ledger_amount)
        return {
            "transaction_id": result.transaction_id,
            "exception_type": result.exception_type,
            "payment_amount": payment_amount,
            "bank_amount": bank_amount,
            "ledger_amount": ledger_amount,
            "difference": difference,
            "recommended_action": result.recommended_action,
        }

    def create_analysis_batch(
        self,
        payment_content: str | bytes,
        bank_content: str | bytes,
        ledger_content: str | bytes,
        payment_filename: str = "payment.csv",
        bank_filename: str = "bank.csv",
        ledger_filename: str = "ledger.csv",
        batch_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        batch_id = f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

        payment_records = parse_csv_records(payment_content, "payment", filename=payment_filename)
        bank_records = parse_csv_records(bank_content, "bank", filename=bank_filename)
        ledger_records = parse_csv_records(ledger_content, "ledger", filename=ledger_filename)

        results = match_records(payment_records, bank_records, ledger_records)
        duration_s = max(time.perf_counter() - start_time, 0.0001)
        duration_ms = Decimal(str(round(duration_s * 1000, 2)))
        total_records = len(results)
        throughput_rps = Decimal(str(round(total_records / duration_s, 2))) if total_records > 0 else Decimal("0.00")

        matched_count = sum(1 for r in results if r.matched)
        exception_count = sum(1 for r in results if not r.matched)
        match_rate = Decimal(str(round((matched_count / total_records * 100) if total_records else 0, 2)))

        exception_breakdown: Dict[str, int] = {}
        for r in results:
            if r.exception_type:
                exception_breakdown[r.exception_type] = exception_breakdown.get(r.exception_type, 0) + 1

        batch = self.repo.save_analysis_batch(
            batch_id=batch_id,
            batch_name=batch_name or f"Analysis Run {batch_id}",
            status="COMPLETED",
            payment_filename=payment_filename,
            bank_filename=bank_filename,
            ledger_filename=ledger_filename,
            total_records=total_records,
            matched_count=matched_count,
            exception_count=exception_count,
            match_rate=match_rate,
            processing_duration_ms=duration_ms,
            throughput_rps=throughput_rps,
            exception_breakdown=exception_breakdown,
            summary_metadata={
                "payment_count": len(payment_records),
                "bank_count": len(bank_records),
                "ledger_count": len(ledger_records),
            },
        )

        for p in payment_records:
            self.repo.save_payment_record(p, batch_id=batch_id)
            self.repo.save_normalized_transaction(p, batch_id=batch_id)
        for b in bank_records:
            self.repo.save_bank_record(b, batch_id=batch_id)
        for l in ledger_records:
            self.repo.save_ledger_record(l, batch_id=batch_id)

        for result in results:
            if not result.exception_type:
                continue
            rec = self._build_exception_record_for_records(result, payment_records, bank_records, ledger_records)
            audit_entry = self.audit_store.create_record(
                transaction_id=rec["transaction_id"],
                match_status="EXCEPTION",
                exception_type=rec["exception_type"],
                payment_amount=float(rec["payment_amount"]) if rec["payment_amount"] is not None else None,
                bank_amount=float(rec["bank_amount"]) if rec["bank_amount"] is not None else None,
                ledger_amount=float(rec["ledger_amount"]) if rec["ledger_amount"] is not None else None,
                difference=float(rec["difference"]) if rec["difference"] is not None else None,
                recommended_action=rec["recommended_action"],
                batch_id=batch_id,
            )
            exc_id = f"EX-{audit_entry['audit_id'].split('-')[-1]}"
            self.repo.save_exception(
                exception_id=exc_id,
                audit_id=audit_entry["audit_id"],
                transaction_id=rec["transaction_id"],
                exception_type=rec["exception_type"],
                recommended_action=rec["recommended_action"],
                severity=self._severity_from_exception(rec["exception_type"]),
                payment_amount=rec["payment_amount"],
                bank_amount=rec["bank_amount"],
                ledger_amount=rec["ledger_amount"],
                difference=rec["difference"],
                review_status="PENDING",
                batch_id=batch_id,
            )

        self.active_batch_id = batch_id
        self.results = results
        self.payment_records = payment_records
        self.bank_records = bank_records
        self.ledger_records = ledger_records

        return self._serialize_batch(batch)

    def list_batches(self) -> List[Dict[str, Any]]:
        batches = self.repo.list_analysis_batches()
        return [self._serialize_batch(b) for b in batches]

    def get_batch(self, batch_id: str) -> Dict[str, Any]:
        batch = self.repo.get_analysis_batch(batch_id)
        if not batch:
            raise KeyError(f"Batch {batch_id} not found.")
        return self._serialize_batch(batch)

    def _serialize_batch(self, batch: AnalysisBatchModel) -> Dict[str, Any]:
        return {
            "batch_id": batch.batch_id,
            "batch_name": batch.batch_name,
            "status": batch.status,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "payment_filename": batch.payment_filename,
            "bank_filename": batch.bank_filename,
            "ledger_filename": batch.ledger_filename,
            "total_records": batch.total_records,
            "matched_count": batch.matched_count,
            "exception_count": batch.exception_count,
            "match_rate": float(batch.match_rate) if batch.match_rate is not None else 0.0,
            "processing_duration_ms": float(batch.processing_duration_ms) if batch.processing_duration_ms is not None else 0.0,
            "throughput_rps": float(batch.throughput_rps) if batch.throughput_rps is not None else 0.0,
            "exception_breakdown": batch.exception_breakdown or {},
            "summary_metadata": batch.summary_metadata or {},
        }

    def _results_for_batch(self, batch_id: Optional[str] = None) -> List[ReconciliationResult]:
        if batch_id is None or (self.active_batch_id and batch_id == self.active_batch_id):
            return self.results
        query_p = self.db.query(PaymentRecordModel).filter(PaymentRecordModel.batch_id == batch_id).all()
        query_b = self.db.query(BankRecordModel).filter(BankRecordModel.batch_id == batch_id).all()
        query_l = self.db.query(LedgerRecordModel).filter(LedgerRecordModel.batch_id == batch_id).all()
        p_recs = [
            TransactionRecord(
                transaction_id=p.transaction_id,
                source_system="payment",
                amount=p.amount,
                currency=p.currency,
                transaction_date=p.transaction_date,
                status=p.status,
                reference_id=p.reference_id,
                customer_id=p.customer_id,
                order_id=p.order_id,
                raw=p.raw_payload or {},
            )
            for p in query_p
        ]
        b_recs = [
            TransactionRecord(
                transaction_id=b.transaction_id,
                source_system="bank",
                amount=b.amount,
                currency=b.currency,
                transaction_date=b.transaction_date,
                status=b.status,
                reference_id=b.reference_id,
                raw=b.raw_payload or {},
            )
            for b in query_b
        ]
        l_recs = [
            TransactionRecord(
                transaction_id=l.transaction_id,
                source_system="ledger",
                amount=l.amount,
                currency=l.currency,
                transaction_date=l.transaction_date,
                status=l.status,
                reference_id=l.reference_id,
                raw=l.raw_payload or {},
            )
            for l in query_l
        ]
        return match_records(p_recs, b_recs, l_recs) if (p_recs or b_recs or l_recs) else []

    def _seed_audit_records(self) -> None:
        for result in self.results:
            if not result.exception_type:
                continue
            record = self._build_exception_record(result)
            audit_entry = self.audit_store.create_record(
                transaction_id=record["transaction_id"],
                match_status="EXCEPTION",
                exception_type=record["exception_type"],
                payment_amount=record["payment_amount"],
                bank_amount=record["bank_amount"],
                ledger_amount=record["ledger_amount"],
                difference=record["difference"],
                recommended_action=record["recommended_action"],
            )
            exc_id = f"EX-{audit_entry['audit_id'].split('-')[-1]}"
            self.repo.save_exception(
                exception_id=exc_id,
                audit_id=audit_entry["audit_id"],
                transaction_id=record["transaction_id"],
                exception_type=record["exception_type"],
                recommended_action=record["recommended_action"],
                severity=self._severity_from_exception(record["exception_type"]),
                payment_amount=record["payment_amount"] if isinstance(record["payment_amount"], Decimal) else (Decimal(str(record["payment_amount"])) if record["payment_amount"] is not None else None),
                bank_amount=record["bank_amount"] if isinstance(record["bank_amount"], Decimal) else (Decimal(str(record["bank_amount"])) if record["bank_amount"] is not None else None),
                ledger_amount=record["ledger_amount"] if isinstance(record["ledger_amount"], Decimal) else (Decimal(str(record["ledger_amount"])) if record["ledger_amount"] is not None else None),
                difference=record["difference"] if isinstance(record["difference"], Decimal) else (Decimal(str(record["difference"])) if record["difference"] is not None else None),
                review_status="PENDING",
            )

    def _build_exception_record(self, result: Any) -> Dict[str, Any]:
        payment = next((item for item in self.payment_records if item.transaction_id == result.transaction_id), None)
        bank = next((item for item in self.bank_records if item.transaction_id == result.transaction_id), None)
        ledger = next((item for item in self.ledger_records if item.transaction_id == result.transaction_id), None)
        payment_amount = payment.amount if payment else None
        bank_amount = bank.amount if bank else None
        ledger_amount = ledger.amount if ledger else None
        difference: Optional[Decimal] = None
        if payment_amount is not None and bank_amount is not None:
            difference = abs(payment_amount - bank_amount)
        elif payment_amount is not None and ledger_amount is not None:
            difference = abs(payment_amount - ledger_amount)
        return {
            "transaction_id": result.transaction_id,
            "exception_type": result.exception_type,
            "payment_amount": payment_amount,
            "bank_amount": bank_amount,
            "ledger_amount": ledger_amount,
            "difference": difference,
            "recommended_action": result.recommended_action,
        }

    def _transaction_payload(self, transaction_id: str) -> Dict[str, Any]:
        payment = next((record for record in self.payment_records if record.transaction_id == transaction_id), None)
        bank = next((record for record in self.bank_records if record.transaction_id == transaction_id), None)
        ledger = next((record for record in self.ledger_records if record.transaction_id == transaction_id), None)
        matching = next((result for result in self.results if result.transaction_id == transaction_id), None)
        return {
            "transaction_id": transaction_id,
            "source_records": {
                key: self._serialize_record(value)
                for key, value in {"payment": payment, "bank": bank, "ledger": ledger}.items()
                if value is not None
            },
            "normalized_values": {
                "payment": str(payment.amount) if payment else None,
                "bank": str(bank.amount) if bank else None,
                "ledger": str(ledger.amount) if ledger else None,
            },
            "reconciliation_result": self._serialize_result(matching) if matching else None,
        }

    def _serialize_record(self, record: TransactionRecord) -> Dict[str, Any]:
        return {
            "transaction_id": record.transaction_id,
            "source_system": record.source_system,
            "amount": str(record.amount),
            "currency": record.currency,
            "transaction_date": record.transaction_date.isoformat() if record.transaction_date else None,
            "status": record.status,
            "reference_id": record.reference_id,
            "customer_id": record.customer_id,
            "order_id": record.order_id,
        }

    def _serialize_result(self, result: Any) -> Dict[str, Any]:
        return {
            "transaction_id": result.transaction_id,
            "matched": result.matched,
            "match_score": result.match_score,
            "exception_type": result.exception_type,
            "explanations": result.explanations,
            "recommended_action": result.recommended_action,
            "details": result.details,
        }

    def _serialize_exception(self, record: Dict[str, Any]) -> Dict[str, Any]:
        exception_id = record.get("exception_id") or f"EX-{record['audit_id'].split('-')[-1]}"
        transaction_id = record.get("transaction_id")
        return {
            "exception_id": exception_id,
            "audit_id": record.get("audit_id"),
            "transaction_id": transaction_id,
            "exception_type": record.get("exception_type"),
            "severity": self._severity_from_exception(record.get("exception_type")),
            "difference": record.get("difference"),
            "recommended_action": record.get("recommended_action"),
            "review_status": record.get("review_status", ReviewState.PENDING.value),
            "reason": record.get("exception_type"),
            "review_history": record.get("review_history", []),
            "transaction": self._transaction_payload(transaction_id) if transaction_id else None,
        }

    def _find_exception_record(self, exception_id: str) -> Optional[Dict[str, Any]]:
        target_num = exception_id.replace("EX-", "").replace("AUD-", "").lstrip("0")
        for record in self.audit_store._read():
            rec_exc_id = record.get("exception_id") or ""
            rec_aud_id = record.get("audit_id") or ""
            if rec_exc_id == exception_id or rec_aud_id == exception_id:
                return record
            rec_num = rec_exc_id.replace("EX-", "").replace("AUD-", "").lstrip("0")
            if rec_num and rec_num == target_num:
                return record
        return None

    def _severity_from_exception(self, exception_type: Optional[str]) -> str:
        if exception_type in {"amount_mismatch", "status_mismatch", "date_mismatch"}:
            return "MEDIUM"
        if exception_type in {"missing_bank", "missing_ledger", "missing_payment"}:
            return "HIGH"
        return "LOW"

    def list_transactions(
        self,
        status: Optional[str] = None,
        exception_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = self._results_for_batch(batch_id)
        items = []
        for result in results:
            if transaction_id and result.transaction_id != transaction_id:
                continue
            if exception_type and result.exception_type != exception_type:
                continue
            if status:
                current_status = "MATCHED" if result.matched else "EXCEPTION"
                if current_status.upper() != status.upper():
                    continue
            items.append(
                {
                    "transaction_id": result.transaction_id,
                    "status": "MATCHED" if result.matched else "EXCEPTION",
                    "exception_type": result.exception_type,
                    "match_score": result.match_score,
                    "recommended_action": result.recommended_action,
                    "details": result.details,
                }
            )
        return items

    def get_transaction(self, transaction_id: str) -> Dict[str, Any]:
        payload = self._transaction_payload(transaction_id)
        if not payload["source_records"] and payload["reconciliation_result"] is None:
            raise KeyError("Transaction not found.")
        return payload

    def list_exceptions(
        self,
        exception_type: Optional[str] = None,
        review_status: Optional[str] = None,
        severity: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        items = []
        target_batch = batch_id or self.active_batch_id
        if not target_batch:
            return []
        for record in self.audit_store._read():
            if record.get("batch_id") != target_batch:
                continue
            if record.get("exception_id") is None:
                record["exception_id"] = f"EX-{record['audit_id'].split('-')[-1]}"
                self.audit_store.update_record(record["audit_id"], record)
            if exception_type and record.get("exception_type") != exception_type:
                continue
            if review_status and record.get("review_status") != review_status.upper():
                continue
            if severity and self._severity_from_exception(record.get("exception_type")) != severity.upper():
                continue
            items.append(self._serialize_exception(record))
        return items

    def get_exception(self, exception_id: str) -> Dict[str, Any]:
        record = self._find_exception_record(exception_id)
        if record is None:
            raise KeyError("Exception not found.")
        return self._serialize_exception(record)

    def investigate_exception(self, exception_id: str) -> Dict[str, Any]:
        record = self._find_exception_record(exception_id)
        if record is None:
            raise KeyError("Exception not found.")
        tx_id = record["transaction_id"]
        payload = self._transaction_payload(tx_id)

        source_records = payload.get("source_records") or {}
        p_rec = source_records.get("payment")
        b_rec = source_records.get("bank")
        l_rec = source_records.get("ledger")

        legs_present = [leg for leg in ["payment", "bank", "ledger"] if leg in source_records]
        missing_legs = [leg for leg in ["payment", "bank", "ledger"] if leg not in source_records]

        # Calculate or extract Decimal difference
        p_amt = Decimal(payload["normalized_values"]["payment"]) if payload["normalized_values"].get("payment") is not None else None
        b_amt = Decimal(payload["normalized_values"]["bank"]) if payload["normalized_values"].get("bank") is not None else None
        l_amt = Decimal(payload["normalized_values"]["ledger"]) if payload["normalized_values"].get("ledger") is not None else None

        diff: Optional[Decimal] = None
        if record.get("difference") is not None:
            diff = Decimal(str(record["difference"]))
        elif p_amt is not None and b_amt is not None and p_amt != b_amt:
            diff = abs(p_amt - b_amt)
        elif p_amt is not None and l_amt is not None and p_amt != l_amt:
            diff = abs(p_amt - l_amt)
        elif b_amt is not None and l_amt is not None and b_amt != l_amt:
            diff = abs(b_amt - l_amt)

        # Factual evidence only: strictly zero ground truth, no heuristic shortcuts
        evidence_collected = {
            "transaction_id": tx_id,
            "exception_type": record.get("exception_type"),
            "payment_amount": p_amt,
            "bank_amount": b_amt,
            "ledger_amount": l_amt,
            "difference": diff,
            "payment_date": p_rec.get("transaction_date") if p_rec else None,
            "bank_date": b_rec.get("transaction_date") if b_rec else None,
            "ledger_date": l_rec.get("transaction_date") if l_rec else None,
            "payment_status": p_rec.get("status") if p_rec else None,
            "bank_status": b_rec.get("status") if b_rec else None,
            "ledger_status": l_rec.get("status") if l_rec else None,
            "reference_id": (p_rec or b_rec or l_rec or {}).get("reference_id"),
            "customer_id": (p_rec or b_rec or l_rec or {}).get("customer_id"),
            "order_id": (p_rec or b_rec or l_rec or {}).get("order_id"),
            "legs_present": legs_present,
            "missing_legs": missing_legs,
        }

        provider_name = getattr(self.agent.provider, "provider_name", "real_llm")
        investigation = self.agent.investigate_exception(
            exception={
                "exception_id": record.get("exception_id") or record["audit_id"],
                "transaction_id": tx_id,
                "exception_type": record.get("exception_type"),
            },
            evidence=evidence_collected,
            source=provider_name,
        )

        # Serialized evidence for JSON responses (amounts as floats or string representation for API)
        serialized_evidence = dict(investigation.get("evidence_collected", {}))
        for k in ["payment_amount", "bank_amount", "ledger_amount", "difference"]:
            if serialized_evidence.get(k) is not None:
                serialized_evidence[k] = float(serialized_evidence[k])

        rec_action = investigation.get("recommended_action") or investigation.get("recommendation") or "REVIEW"
        if rec_action == "ESCALATED":
            rec_action = "ESCALATE"

        return {
            "investigation_id": investigation["investigation_id"],
            "exception_id": record.get("exception_id") or record["audit_id"],
            "exception_type": record.get("exception_type"),
            "investigation_status": investigation["agent_status"],
            "diagnosis": investigation.get("diagnosis") or investigation.get("summary", "Insufficient evidence."),
            "likely_cause": investigation.get("likely_cause") or investigation.get("most_likely_cause", "UNKNOWN"),
            "confidence": investigation.get("confidence", "LOW"),
            "evidence": serialized_evidence,
            "evidence_statements": investigation.get("evidence_statements", []),
            "limitations": investigation.get("limitations", []),
            "recommended_action": rec_action,
            "requires_human_review": investigation.get("requires_human_review", True),
            # Legacy backward-compatible fields
            "summary": investigation.get("summary", "Insufficient evidence."),
            "findings": investigation.get("findings", []),
            "possible_causes": investigation.get("possible_causes", []),
            "most_likely_cause": investigation.get("most_likely_cause", "UNKNOWN"),
            "recommendation": investigation.get("recommendation", "Manual investigation required."),
        }

    def review_exception(self, exception_id: str, decision: str, reviewer: str, comment: str) -> Dict[str, Any]:
        record = self._find_exception_record(exception_id)
        if record is None:
            raise KeyError("Exception not found.")
        target = record["audit_id"]
        updated = transition_review_state(self.audit_store, target, ReviewState(decision), reviewer, comment)

        # Persist review in database
        self.repo.add_review(
            exception_id=record.get("exception_id") or target,
            previous_state=record.get("review_status", "PENDING"),
            new_state=decision,
            reviewer=reviewer,
            comment=comment,
        )

        return {
            "exception_id": record.get("exception_id") or target,
            "audit_id": target,
            "review_status": updated["review_status"],
            "review_history": updated["review_history"],
            "reviewer": updated.get("reviewer"),
            "comment": updated.get("reviewer_comment"),
        }

    def get_review_history(self, exception_id: str) -> List[Dict[str, Any]]:
        record = self._find_exception_record(exception_id)
        if record is None:
            raise KeyError("Exception not found.")
        return record.get("review_history", [])

    def get_audit_history(self, transaction_id: str, batch_id: Optional[str] = None) -> Dict[str, Any]:
        target_batch = batch_id or self.active_batch_id
        if target_batch:
            txn_records = [
                record for record in self.audit_store._read()
                if record.get("transaction_id") == transaction_id and record.get("batch_id") == target_batch
            ]
        else:
            txn_records = [record for record in self.audit_store._read() if record.get("transaction_id") == transaction_id]

        investigations = [
            {
                "investigation_id": item["investigation_id"],
                "exception_id": item.get("exception_id"),
                "status": item.get("agent_status"),
                "summary": item.get("summary"),
            }
            for item in self.investigation_store._read()
            if item.get("exception_id")
            and any(
                r.get("transaction_id") == transaction_id
                and (r.get("exception_id") == item.get("exception_id") or r.get("audit_id") == item.get("exception_id"))
                for r in txn_records
            )
        ]
        return {
            "transaction_id": transaction_id,
            "audit_records": txn_records,
            "exception_information": [self._serialize_exception(record) for record in txn_records],
            "investigations": investigations,
            "review_actions": [entry for record in txn_records for entry in record.get("review_history", [])],
        }

    def get_reconciliation_report(self, batch_id: Optional[str] = None) -> Dict[str, Any]:
        results = self._results_for_batch(batch_id)
        return build_summary(results)

    def get_exception_report(self, batch_id: Optional[str] = None) -> Dict[str, Any]:
        results = self._results_for_batch(batch_id)
        return build_exception_report(results)

    def export_exceptions(self, fmt: str = "json", batch_id: Optional[str] = None) -> Tuple[bytes, str]:
        results = self._results_for_batch(batch_id)
        output_path = self.data_dir / f"exceptions_export.{fmt.lower()}"
        export_exception_report_helper(results, output_path, fmt=fmt.lower())
        content = output_path.read_bytes()
        media_type = "application/json" if fmt.lower() == "json" else "text/csv"
        return content, media_type

    def answer_copilot_query(
        self,
        query: str,
        batch_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        target_batch_id = batch_id or self.active_batch_id
        if not target_batch_id:
            batches = self.list_batches()
            if batches:
                target_batch_id = batches[0]["batch_id"]

        recon_report = self.get_reconciliation_report(batch_id=target_batch_id) if target_batch_id else {}
        exc_report = self.get_exception_report(batch_id=target_batch_id) if target_batch_id else {}
        exceptions = self.list_exceptions(batch_id=target_batch_id) if target_batch_id else []

        batch_metadata = {}
        if target_batch_id:
            try:
                batch_metadata = self.get_batch(target_batch_id)
            except Exception:
                pass

        import re
        query_tx_ids = re.findall(r"\bTX[A-Za-z0-9_-]+\b", query)
        query_ex_ids = re.findall(r"\bEX-[A-Za-z0-9_-]+\b", query)

        relevant_txns = []
        target_tx_set = set(query_tx_ids)
        for ex in exceptions:
            if ex.get("exception_id") in query_ex_ids and ex.get("transaction_id"):
                target_tx_set.add(ex["transaction_id"])

        if not target_tx_set:
            for ex in exceptions[:5]:
                if ex.get("transaction_id"):
                    target_tx_set.add(ex["transaction_id"])

        for tx_id in target_tx_set:
            try:
                tx_payload = self.get_transaction(tx_id)
                relevant_txns.append(tx_payload)
            except Exception:
                pass

        batch_context = {
            "batch_id": target_batch_id,
            "batch_name": batch_metadata.get("batch_name", "Active Run"),
            "total_records": recon_report.get("total_records", 0),
            "matched_count": recon_report.get("matched", 0),
            "exception_count": recon_report.get("unresolved", 0),
            "match_rate": recon_report.get("match_rate", 0),
            "net_variance": exc_report.get("total_financial_difference", 0),
            "exception_breakdown": recon_report.get("exception_breakdown", {}),
            "exceptions_summary": [
                {
                    "exception_id": e.get("exception_id"),
                    "transaction_id": e.get("transaction_id"),
                    "exception_type": e.get("exception_type"),
                    "difference": e.get("difference"),
                    "review_status": e.get("review_status"),
                    "recommended_action": e.get("recommended_action"),
                }
                for e in exceptions[:15]
            ],
        }

        copilot = FinanceCopilotAgent(provider=self.agent.provider)
        return copilot.answer_query(
            query=query,
            batch_context=batch_context,
            transaction_evidence=relevant_txns,
            history=history,
        )


class FinanceAPI:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        data_dir: Optional[str | Path] = None,
        seed_on_empty: bool = False,
    ) -> None:
        self.service = FinanceService(data_dir=data_dir, seed_on_empty=seed_on_empty)
        self.host = host
        self.port = port
        self._thread = None
        self._server = ThreadingHTTPServer((host, port), self._handler_class())
        self.port = self._server.server_address[1]

    def _handler_class(self):
        service = self.service

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self._handle_request("GET")

            def do_POST(self):
                self._handle_request("POST")

            def _handle_request(self, method: str) -> None:
                parsed = urlparse(self.path)
                path = parsed.path
                query = parse_qs(parsed.query)
                body = {}
                if method == "POST":
                    length = int(self.headers.get("Content-Length", "0"))
                    if length:
                        try:
                            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                        except json.JSONDecodeError:
                            body = {}
                params = {key: values[0] if values else None for key, values in query.items()}
                try:
                    payload, status_code, media_type = self._dispatch(path, method, params, body)
                    self.send_response(status_code)
                    self.send_header("Content-Type", media_type)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    if payload is not None:
                        if media_type == "application/json":
                            self.wfile.write(json.dumps(payload).encode("utf-8"))
                        else:
                            self.wfile.write(payload if isinstance(payload, bytes) else str(payload).encode("utf-8"))
                except Exception as exc:
                    import traceback
                    traceback.print_exc()
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "INTERNAL_SERVER_ERROR", "message": str(exc)}).encode("utf-8"))

            def _dispatch(self, path: str, method: str, params: Dict[str, str], body: Dict[str, Any]):
                if path == "/health":
                    return {"status": "ok"}, 200, "application/json"
                if path == "/":
                    return {"status": "ok"}, 200, "application/json"
                if path == "/ai/status":
                    provider = service.agent.provider
                    provider_name = getattr(provider, "provider_name", "UNCONFIGURED")
                    is_configured = provider_name != "UNCONFIGURED"
                    return {
                        "status": "CONFIGURED" if is_configured else "UNCONFIGURED",
                        "provider": provider_name,
                        "requires_key": not is_configured,
                    }, 200, "application/json"
                if path == "/analysis":
                    if method == "POST":
                        p_data = body.get("payment_data") or body.get("payment_file") or ""
                        b_data = body.get("bank_data") or body.get("bank_file") or ""
                        l_data = body.get("ledger_data") or body.get("ledger_file") or ""
                        try:
                            res = service.create_analysis_batch(
                                payment_content=p_data,
                                bank_content=b_data,
                                ledger_content=l_data,
                                payment_filename=body.get("payment_filename", "payment.csv"),
                                bank_filename=body.get("bank_filename", "bank.csv"),
                                ledger_filename=body.get("ledger_filename", "ledger.csv"),
                                batch_name=body.get("batch_name"),
                            )
                            return res, 201, "application/json"
                        except ValueError as exc:
                            return {"error": "INVALID_FILE_FORMAT", "message": str(exc)}, 400, "application/json"
                    return service.list_batches(), 200, "application/json"
                if path.startswith("/analysis/"):
                    sub = path.split("/analysis/", 1)[1]
                    if "/transactions" in sub:
                        batch_id = sub.split("/transactions")[0]
                        return service.list_transactions(batch_id=batch_id), 200, "application/json"
                    if "/exceptions" in sub:
                        batch_id = sub.split("/exceptions")[0]
                        return service.list_exceptions(batch_id=batch_id), 200, "application/json"
                    if "/reports" in sub:
                        batch_id = sub.split("/reports")[0]
                        return {
                            "reconciliation": service.get_reconciliation_report(batch_id=batch_id),
                            "exceptions": service.get_exception_report(batch_id=batch_id),
                        }, 200, "application/json"
                    batch_id = sub
                    try:
                        return service.get_batch(batch_id), 200, "application/json"
                    except KeyError:
                        return {"error": "BATCH_NOT_FOUND", "message": f"Batch {batch_id} was not found."}, 404, "application/json"
                if path == "/transactions":
                    return service.list_transactions(
                        status=params.get("status"),
                        exception_type=params.get("exception_type"),
                        transaction_id=params.get("transaction_id"),
                        batch_id=params.get("batch_id"),
                    ), 200, "application/json"
                if path.startswith("/transactions/"):
                    txn_id = path.split("/transactions/", 1)[1]
                    if not txn_id:
                        return {"error": "INVALID_REQUEST", "message": "Transaction ID is required."}, 400, "application/json"
                    try:
                        return service.get_transaction(txn_id), 200, "application/json"
                    except KeyError:
                        return {"error": "TRANSACTION_NOT_FOUND", "message": "Transaction not found."}, 404, "application/json"
                if path == "/exceptions":
                    return service.list_exceptions(
                        exception_type=params.get("exception_type"),
                        review_status=params.get("review_status"),
                        severity=params.get("severity"),
                        batch_id=params.get("batch_id"),
                    ), 200, "application/json"
                if path.startswith("/exceptions/"):
                    remainder = path.split("/exceptions/", 1)[1]
                    if "/reviews" in remainder:
                        exception_id = remainder.split("/reviews", 1)[0]
                        try:
                            return service.get_review_history(exception_id), 200, "application/json"
                        except KeyError:
                            return {"error": "EXCEPTION_NOT_FOUND", "message": f"Exception {exception_id} was not found."}, 404, "application/json"
                    elif "/investigate" in remainder:
                        exception_id = remainder.split("/investigate", 1)[0]
                        try:
                            return service.investigate_exception(exception_id), 200, "application/json"
                        except AIConfigurationError as exc:
                            return {"error": "AI_UNCONFIGURED", "message": str(exc)}, 422, "application/json"
                        except AIProviderError as exc:
                            return {"error": "AI_PROVIDER_ERROR", "message": str(exc)}, 503, "application/json"
                        except KeyError:
                            return {"error": "EXCEPTION_NOT_FOUND", "message": f"Exception {exception_id} was not found."}, 404, "application/json"
                    elif "/review" in remainder:
                        exception_id = remainder.split("/review", 1)[0]
                        if method != "POST":
                            return {"error": "INVALID_METHOD", "message": "POST is required."}, 405, "application/json"
                        decision = str(body.get("decision") or "").upper()
                        reviewer = str(body.get("reviewer") or "").strip()
                        comment = str(body.get("comment") or "")
                        if decision not in {"APPROVED", "REJECTED", "ESCALATED"}:
                            return {"error": "INVALID_REVIEW_DECISION", "message": "Decision must be APPROVED, REJECTED, or ESCALATED."}, 400, "application/json"
                        if not reviewer:
                            return {"error": "VALIDATION_ERROR", "message": "Reviewer must not be empty."}, 422, "application/json"
                        try:
                            return service.review_exception(exception_id, decision, reviewer, comment), 200, "application/json"
                        except KeyError:
                            return {"error": "EXCEPTION_NOT_FOUND", "message": f"Exception {exception_id} was not found."}, 404, "application/json"
                        except ValueError as exc:
                            return {"error": "INVALID_REVIEW_TRANSITION", "message": str(exc)}, 409, "application/json"
                    exception_id = remainder
                    try:
                        return service.get_exception(exception_id), 200, "application/json"
                    except KeyError:
                        return {"error": "EXCEPTION_NOT_FOUND", "message": f"Exception {exception_id} was not found."}, 404, "application/json"
                if path == "/audit":
                    return {"error": "INVALID_REQUEST", "message": "Transaction ID is required."}, 400, "application/json"
                if path.startswith("/audit/"):
                    transaction_id = path.split("/audit/", 1)[1]
                    return service.get_audit_history(transaction_id, batch_id=params.get("batch_id")), 200, "application/json"
                if path == "/reports/reconciliation":
                    return service.get_reconciliation_report(batch_id=params.get("batch_id")), 200, "application/json"
                if path == "/reports/exceptions":
                    return service.get_exception_report(batch_id=params.get("batch_id")), 200, "application/json"
                if path == "/reports/exceptions/export":
                    fmt = str(params.get("format") or "json").lower()
                    if fmt not in {"json", "csv"}:
                        return {"error": "INVALID_FORMAT", "message": "Format must be json or csv."}, 422, "application/json"
                    data, media = service.export_exceptions(fmt, batch_id=params.get("batch_id"))
                    payload = json.loads(data.decode("utf-8")) if fmt == "json" else data.decode("utf-8")
                    return payload, 200, media
                return {"error": "NOT_FOUND", "message": "Endpoint not found."}, 404, "application/json"

        return Handler

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)


service = FinanceService(
    data_dir=os.getenv("FINANCE_DATA_DIR"),
    seed_on_empty=False,
)
app = FastAPI(title="Finance Controller API")


class ReviewRequest(BaseModel):
    decision: str
    reviewer: str
    comment: str = ""


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/ai/status")
def get_ai_status() -> Dict[str, Any]:
    provider = service.agent.provider
    if hasattr(provider, "reload"):
        provider.reload()
    provider_name = getattr(provider, "provider_name", "UNCONFIGURED")
    is_configured = provider_name != "UNCONFIGURED"
    return {
        "status": "CONFIGURED" if is_configured else "UNCONFIGURED",
        "provider": provider_name,
        "requires_key": not is_configured,
    }


class CopilotQueryRequest(BaseModel):
    query: str
    batch_id: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None


@app.post("/ai/query")
def copilot_query(req: CopilotQueryRequest) -> Dict[str, Any]:
    try:
        return service.answer_copilot_query(
            query=req.query,
            batch_id=req.batch_id,
            history=req.history,
        )
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "AI_UNCONFIGURED", "message": str(exc)},
        ) from exc
    except AIProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "AI_PROVIDER_ERROR", "message": str(exc)},
        ) from exc


@app.post("/analysis")
async def upload_analysis(
    payment_file: UploadFile = File(...),
    bank_file: UploadFile = File(...),
    ledger_file: UploadFile = File(...),
    batch_name: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        p_bytes = await payment_file.read()
        b_bytes = await bank_file.read()
        l_bytes = await ledger_file.read()
        return service.create_analysis_batch(
            payment_content=p_bytes,
            bank_content=b_bytes,
            ledger_content=l_bytes,
            payment_filename=payment_file.filename or "payment.csv",
            bank_filename=bank_file.filename or "bank.csv",
            ledger_filename=ledger_file.filename or "ledger.csv",
            batch_name=batch_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "INVALID_FILE_FORMAT", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "PROCESSING_ERROR", "message": str(exc)}) from exc


@app.get("/analysis")
def list_batches() -> List[Dict[str, Any]]:
    return service.list_batches()


@app.get("/analysis/{batch_id}")
def get_batch(batch_id: str) -> Dict[str, Any]:
    try:
        return service.get_batch(batch_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "BATCH_NOT_FOUND", "message": f"Batch {batch_id} not found."}) from exc


@app.get("/analysis/{batch_id}/transactions")
def get_batch_transactions(batch_id: str) -> List[Dict[str, Any]]:
    return service.list_transactions(batch_id=batch_id)


@app.get("/analysis/{batch_id}/exceptions")
def get_batch_exceptions(batch_id: str) -> List[Dict[str, Any]]:
    return service.list_exceptions(batch_id=batch_id)


@app.get("/analysis/{batch_id}/reports")
def get_batch_reports(batch_id: str) -> Dict[str, Any]:
    return {
        "reconciliation": service.get_reconciliation_report(batch_id=batch_id),
        "exceptions": service.get_exception_report(batch_id=batch_id),
    }


@app.get("/transactions")
def list_transactions(
    status: Optional[str] = None,
    exception_type: Optional[str] = None,
    transaction_id: Optional[str] = None,
    batch_id: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    return service.list_transactions(
        status=status,
        exception_type=exception_type,
        transaction_id=transaction_id,
        batch_id=batch_id,
    )


@app.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str) -> Dict[str, Any]:
    try:
        return service.get_transaction(transaction_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "TRANSACTION_NOT_FOUND", "message": "Transaction not found."}) from exc


@app.get("/exceptions")
def list_exceptions(
    exception_type: Optional[str] = None,
    review_status: Optional[str] = None,
    severity: Optional[str] = None,
    batch_id: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    return service.list_exceptions(
        exception_type=exception_type,
        review_status=review_status,
        severity=severity,
        batch_id=batch_id,
    )


@app.get("/exceptions/{exception_id}")
def get_exception(exception_id: str) -> Dict[str, Any]:
    try:
        return service.get_exception(exception_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "EXCEPTION_NOT_FOUND", "message": f"Exception {exception_id} was not found."}) from exc


@app.post("/exceptions/{exception_id}/investigate")
def investigate_exception(exception_id: str) -> Dict[str, Any]:
    try:
        return service.investigate_exception(exception_id)
    except AIConfigurationError as exc:
        raise HTTPException(status_code=422, detail={"error": "AI_UNCONFIGURED", "message": str(exc)}) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail={"error": "AI_PROVIDER_ERROR", "message": str(exc)}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "EXCEPTION_NOT_FOUND", "message": f"Exception {exception_id} was not found."}) from exc


@app.get("/exceptions/{exception_id}/reviews")
def get_review_history(exception_id: str) -> List[Dict[str, Any]]:
    try:
        return service.get_review_history(exception_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "EXCEPTION_NOT_FOUND", "message": f"Exception {exception_id} was not found."}) from exc


@app.post("/exceptions/{exception_id}/review")
def review_exception(exception_id: str, payload: ReviewRequest) -> Dict[str, Any]:
    decision = payload.decision.upper()
    if decision not in {"APPROVED", "REJECTED", "ESCALATED"}:
        raise HTTPException(status_code=400, detail={"error": "INVALID_REVIEW_DECISION", "message": "Decision must be APPROVED, REJECTED, or ESCALATED."})
    if not payload.reviewer.strip():
        raise HTTPException(status_code=422, detail={"error": "VALIDATION_ERROR", "message": "Reviewer must not be empty."})
    try:
        return service.review_exception(exception_id, decision, payload.reviewer, payload.comment)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "EXCEPTION_NOT_FOUND", "message": f"Exception {exception_id} was not found."}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error": "INVALID_REVIEW_TRANSITION", "message": str(exc)}) from exc


@app.get("/audit/{transaction_id}")
def get_audit_history(transaction_id: str, batch_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    return service.get_audit_history(transaction_id, batch_id=batch_id)


@app.get("/reports/reconciliation")
def get_reconciliation_report(batch_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    return service.get_reconciliation_report(batch_id=batch_id)


@app.get("/reports/exceptions")
def get_exception_report(batch_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    return service.get_exception_report(batch_id=batch_id)


@app.get("/reports/exceptions/export")
def export_exception_report_endpoint(format: str = "json", batch_id: Optional[str] = Query(None)) -> Any:
    fmt = format.lower()
    if fmt not in {"json", "csv"}:
        raise HTTPException(status_code=422, detail={"error": "INVALID_FORMAT", "message": "Format must be json or csv."})
    data, media = service.export_exceptions(fmt, batch_id=batch_id)
    if fmt == "json":
        return json.loads(data.decode("utf-8"))
    return data.decode("utf-8")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api:app", host="127.0.0.1", port=8000, reload=False)
