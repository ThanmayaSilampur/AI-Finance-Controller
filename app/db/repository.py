from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.db.models import (
    AnalysisBatchModel,
    AuditEventModel,
    BankRecordModel,
    ExceptionModel,
    InvestigationModel,
    LedgerRecordModel,
    PaymentRecordModel,
    RawTransaction,
    ReviewModel,
    TransactionModel,
)
from app.models import ReconciliationResult, TransactionRecord


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DatabaseRepository:
    """Repository abstraction encapsulating all PostgreSQL / SQLAlchemy operations."""

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # Raw Transactions Layer
    # -------------------------------------------------------------------------
    def save_raw_transaction(
        self,
        source_dataset: str,
        source_record_id: str,
        raw_payload: Dict[str, Any],
        status: str = "INGESTED",
        error_message: Optional[str] = None,
    ) -> RawTransaction:
        """Store raw incoming transaction with source lineage."""
        # Check idempotency
        stmt = select(RawTransaction).where(
            RawTransaction.source_dataset == source_dataset,
            RawTransaction.source_record_id == source_record_id,
        )
        existing = self.db.execute(stmt).scalar_one_or_none()
        if existing:
            existing.raw_payload = raw_payload
            existing.status = status
            existing.error_message = error_message
            self.db.commit()
            self.db.refresh(existing)
            return existing

        raw = RawTransaction(
            source_dataset=source_dataset,
            source_record_id=source_record_id,
            raw_payload=raw_payload,
            status=status,
            error_message=error_message,
        )
        self.db.add(raw)
        self.db.commit()
        self.db.refresh(raw)
        return raw

    def get_raw_transaction(self, raw_id: int) -> Optional[RawTransaction]:
        return self.db.get(RawTransaction, raw_id)

    def list_raw_transactions(self, source_dataset: Optional[str] = None) -> List[RawTransaction]:
        stmt = select(RawTransaction)
        if source_dataset:
            stmt = stmt.where(RawTransaction.source_dataset == source_dataset)
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Normalized Financial Transactions Layer
    # -------------------------------------------------------------------------
    def save_normalized_transaction(
        self,
        transaction: TransactionRecord,
        raw_transaction_id: Optional[int] = None,
        batch_id: Optional[str] = None,
    ) -> TransactionModel:
        """Insert or update normalized transaction record."""
        existing = self.db.get(TransactionModel, transaction.transaction_id)
        if existing:
            existing.source_system = transaction.source_system
            existing.amount = transaction.amount
            existing.currency = transaction.currency
            existing.transaction_date = transaction.transaction_date
            existing.status = transaction.status
            existing.reference_id = transaction.reference_id
            existing.customer_id = transaction.customer_id
            existing.order_id = transaction.order_id
            if raw_transaction_id is not None:
                existing.raw_transaction_id = raw_transaction_id
            if batch_id is not None:
                existing.batch_id = batch_id
            self.db.commit()
            self.db.refresh(existing)
            return existing

        model = TransactionModel(
            transaction_id=transaction.transaction_id,
            batch_id=batch_id,
            raw_transaction_id=raw_transaction_id,
            source_system=transaction.source_system,
            amount=transaction.amount,
            currency=transaction.currency,
            transaction_date=transaction.transaction_date,
            status=transaction.status,
            reference_id=transaction.reference_id,
            customer_id=transaction.customer_id,
            order_id=transaction.order_id,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def list_transactions(self, batch_id: Optional[str] = None) -> List[TransactionModel]:
        stmt = select(TransactionModel)
        if batch_id:
            stmt = stmt.where(TransactionModel.batch_id == batch_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_transaction(self, transaction_id: str) -> Optional[TransactionModel]:
        return self.db.get(TransactionModel, transaction_id)

    # -------------------------------------------------------------------------
    # Reconciliation Streams (Payment, Bank, Ledger)
    # -------------------------------------------------------------------------
    def save_payment_record(self, record: TransactionRecord, batch_id: Optional[str] = None) -> PaymentRecordModel:
        model = PaymentRecordModel(
            transaction_id=record.transaction_id,
            batch_id=batch_id,
            amount=record.amount,
            currency=record.currency,
            transaction_date=record.transaction_date,
            status=record.status,
            reference_id=record.reference_id,
            customer_id=record.customer_id,
            order_id=record.order_id,
            raw_payload=record.raw,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def save_bank_record(self, record: TransactionRecord, batch_id: Optional[str] = None) -> BankRecordModel:
        model = BankRecordModel(
            transaction_id=record.transaction_id,
            batch_id=batch_id,
            amount=record.amount,
            currency=record.currency,
            transaction_date=record.transaction_date,
            status=record.status,
            reference_id=record.reference_id,
            bank_name=record.raw.get("bank_name") or record.raw.get("From Bank"),
            account_id=record.raw.get("account_id") or record.raw.get("Account"),
            raw_payload=record.raw,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def save_ledger_record(self, record: TransactionRecord, batch_id: Optional[str] = None) -> LedgerRecordModel:
        model = LedgerRecordModel(
            transaction_id=record.transaction_id,
            batch_id=batch_id,
            amount=record.amount,
            currency=record.currency,
            transaction_date=record.transaction_date,
            status=record.status,
            reference_id=record.reference_id,
            account_code=record.raw.get("account_code") or record.raw.get("Account.1"),
            raw_payload=record.raw,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    # -------------------------------------------------------------------------
    # Exception Management
    # -------------------------------------------------------------------------
    def save_exception(
        self,
        exception_id: str,
        audit_id: str,
        transaction_id: str,
        exception_type: str,
        recommended_action: str,
        severity: str = "MEDIUM",
        payment_amount: Optional[Decimal] = None,
        bank_amount: Optional[Decimal] = None,
        ledger_amount: Optional[Decimal] = None,
        difference: Optional[Decimal] = None,
        review_status: str = "PENDING",
        batch_id: Optional[str] = None,
    ) -> ExceptionModel:
        existing = self.db.get(ExceptionModel, exception_id)
        if existing:
            existing.review_status = review_status
            if batch_id is not None:
                existing.batch_id = batch_id
            existing.updated_at = utc_now()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        exc = ExceptionModel(
            exception_id=exception_id,
            batch_id=batch_id,
            audit_id=audit_id,
            transaction_id=transaction_id,
            exception_type=exception_type,
            severity=severity,
            payment_amount=payment_amount,
            bank_amount=bank_amount,
            ledger_amount=ledger_amount,
            difference=difference,
            recommended_action=recommended_action,
            review_status=review_status,
        )
        self.db.add(exc)
        self.db.commit()
        self.db.refresh(exc)
        return exc

    def get_exception(self, exception_id: str) -> Optional[ExceptionModel]:
        return self.db.get(ExceptionModel, exception_id)

    def list_exceptions(
        self,
        exception_type: Optional[str] = None,
        review_status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[ExceptionModel]:
        stmt = select(ExceptionModel)
        if exception_type:
            stmt = stmt.where(ExceptionModel.exception_type == exception_type)
        if review_status:
            stmt = stmt.where(ExceptionModel.review_status == review_status.upper())
        if severity:
            stmt = stmt.where(ExceptionModel.severity == severity.upper())
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Reviews
    # -------------------------------------------------------------------------
    def add_review(
        self,
        exception_id: str,
        previous_state: str,
        new_state: str,
        reviewer: str,
        comment: Optional[str] = None,
    ) -> ReviewModel:
        review = ReviewModel(
            exception_id=exception_id,
            previous_state=previous_state,
            new_state=new_state,
            reviewer=reviewer,
            comment=comment,
        )
        self.db.add(review)

        # Update exception state
        exc = self.db.get(ExceptionModel, exception_id)
        if exc:
            exc.review_status = new_state
            exc.updated_at = utc_now()

        # Update matching audit event status fields only.
        # review_history is the sole responsibility of AuditStore.update_record();
        # do NOT append here to avoid duplicate history entries.
        if exc:
            stmt = select(AuditEventModel).where(AuditEventModel.audit_id == exc.audit_id)
            audit = self.db.execute(stmt).scalar_one_or_none()
            if audit:
                audit.review_status = new_state
                audit.reviewer = reviewer
                audit.reviewer_comment = comment
                audit.resolution_timestamp = utc_now()

        self.db.commit()
        self.db.refresh(review)
        return review

    def list_reviews(self, exception_id: str) -> List[ReviewModel]:
        stmt = select(ReviewModel).where(ReviewModel.exception_id == exception_id).order_by(ReviewModel.created_at)
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Investigations
    # -------------------------------------------------------------------------
    def save_investigation(
        self,
        investigation_id: str,
        exception_id: str,
        transaction_id: str,
        provider: str,
        agent_status: str,
        confidence: str,
        summary: str,
        most_likely_cause: str,
        findings: List[Any],
        possible_causes: List[Any],
        evidence_collected: Dict[str, Any],
        tools_used: List[str],
        recommendation: str,
        requires_human_review: bool = True,
    ) -> InvestigationModel:
        existing = self.db.get(InvestigationModel, investigation_id)
        if existing:
            existing.agent_status = agent_status
            existing.confidence = confidence
            existing.summary = summary
            existing.most_likely_cause = most_likely_cause
            existing.findings = findings
            existing.possible_causes = possible_causes
            existing.evidence_collected = evidence_collected
            existing.tools_used = tools_used
            existing.recommendation = recommendation
            existing.requires_human_review = requires_human_review
            self.db.commit()
            self.db.refresh(existing)
            return existing

        inv = InvestigationModel(
            investigation_id=investigation_id,
            exception_id=exception_id,
            transaction_id=transaction_id,
            provider=provider,
            agent_status=agent_status,
            confidence=confidence,
            summary=summary,
            most_likely_cause=most_likely_cause,
            findings=findings,
            possible_causes=possible_causes,
            evidence_collected=evidence_collected,
            tools_used=tools_used,
            recommendation=recommendation,
            requires_human_review=requires_human_review,
        )
        self.db.add(inv)
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def get_investigation(self, investigation_id: str) -> Optional[InvestigationModel]:
        return self.db.get(InvestigationModel, investigation_id)

    def list_investigations_for_transaction(self, transaction_id: str) -> List[InvestigationModel]:
        stmt = select(InvestigationModel).where(InvestigationModel.transaction_id == transaction_id)
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Audit Trail
    # -------------------------------------------------------------------------
    def save_audit_event(
        self,
        audit_id: str,
        transaction_id: str,
        match_status: str,
        exception_type: Optional[str] = None,
        payment_amount: Optional[Decimal] = None,
        bank_amount: Optional[Decimal] = None,
        ledger_amount: Optional[Decimal] = None,
        difference: Optional[Decimal] = None,
        recommended_action: str = "MANUAL_REVIEW",
        review_status: str = "PENDING",
        reviewer: Optional[str] = None,
        reviewer_comment: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> AuditEventModel:
        existing = self.db.get(AuditEventModel, audit_id)
        if existing:
            return existing

        event = AuditEventModel(
            audit_id=audit_id,
            batch_id=batch_id,
            transaction_id=transaction_id,
            match_status=match_status,
            exception_type=exception_type,
            payment_amount=payment_amount,
            bank_amount=bank_amount,
            ledger_amount=ledger_amount,
            difference=difference,
            recommended_action=recommended_action,
            review_status=review_status,
            reviewer=reviewer,
            reviewer_comment=reviewer_comment,
            processing_timestamp=utc_now(),
            review_history=[],
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_audit_event(self, audit_id: str) -> Optional[AuditEventModel]:
        return self.db.get(AuditEventModel, audit_id)

    def list_audit_events_for_transaction(self, transaction_id: str) -> List[AuditEventModel]:
        stmt = select(AuditEventModel).where(AuditEventModel.transaction_id == transaction_id)
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Analysis Batch Layer
    # -------------------------------------------------------------------------
    def save_analysis_batch(
        self,
        batch_id: str,
        batch_name: Optional[str] = None,
        status: str = "COMPLETED",
        payment_filename: Optional[str] = None,
        bank_filename: Optional[str] = None,
        ledger_filename: Optional[str] = None,
        total_records: int = 0,
        matched_count: int = 0,
        exception_count: int = 0,
        match_rate: Decimal = Decimal("0.00"),
        processing_duration_ms: Decimal = Decimal("0.00"),
        throughput_rps: Decimal = Decimal("0.00"),
        exception_breakdown: Optional[Dict[str, Any]] = None,
        summary_metadata: Optional[Dict[str, Any]] = None,
    ) -> AnalysisBatchModel:
        existing = self.db.get(AnalysisBatchModel, batch_id)
        if existing:
            existing.status = status
            existing.matched_count = matched_count
            existing.exception_count = exception_count
            existing.match_rate = match_rate
            existing.processing_duration_ms = processing_duration_ms
            existing.throughput_rps = throughput_rps
            if exception_breakdown is not None:
                existing.exception_breakdown = exception_breakdown
            if summary_metadata is not None:
                existing.summary_metadata = summary_metadata
            self.db.commit()
            self.db.refresh(existing)
            return existing

        batch = AnalysisBatchModel(
            batch_id=batch_id,
            batch_name=batch_name or f"Reconciliation Run {batch_id}",
            status=status,
            payment_filename=payment_filename,
            bank_filename=bank_filename,
            ledger_filename=ledger_filename,
            total_records=total_records,
            matched_count=matched_count,
            exception_count=exception_count,
            match_rate=match_rate,
            processing_duration_ms=processing_duration_ms,
            throughput_rps=throughput_rps,
            exception_breakdown=exception_breakdown or {},
            summary_metadata=summary_metadata or {},
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def get_analysis_batch(self, batch_id: str) -> Optional[AnalysisBatchModel]:
        return self.db.get(AnalysisBatchModel, batch_id)

    def list_analysis_batches(self) -> List[AnalysisBatchModel]:
        stmt = select(AnalysisBatchModel).order_by(AnalysisBatchModel.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())
