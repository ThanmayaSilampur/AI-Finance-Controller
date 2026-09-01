from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RawTransaction(Base):
    __tablename__ = "raw_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_dataset: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    ingestion_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="INGESTED", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    normalized_transactions = relationship("TransactionModel", back_populates="raw_transaction")

    __table_args__ = (
        UniqueConstraint("source_dataset", "source_record_id", name="uq_raw_source_record"),
    )


class TransactionModel(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    raw_transaction_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("raw_transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_system: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    transaction_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="UNKNOWN", nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    raw_transaction = relationship("RawTransaction", back_populates="normalized_transactions")


class PaymentRecordModel(Base):
    __tablename__ = "payment_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    transaction_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BankRecordModel(Base):
    __tablename__ = "bank_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    transaction_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="POSTED", nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class LedgerRecordModel(Base):
    __tablename__ = "ledger_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    transaction_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PAID", nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    account_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ExceptionModel(Base):
    __tablename__ = "exceptions"

    exception_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    audit_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    exception_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    payment_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    bank_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    ledger_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    difference: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    recommended_action: Mapped[str] = mapped_column(String(255), nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    reviews = relationship("ReviewModel", back_populates="exception_record", cascade="all, delete-orphan")
    investigations = relationship("InvestigationModel", back_populates="exception_record", cascade="all, delete-orphan")


class ReviewModel(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exception_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("exceptions.exception_id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_state: Mapped[str] = mapped_column(String(50), nullable=False)
    new_state: Mapped[str] = mapped_column(String(50), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(100), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    exception_record = relationship("ExceptionModel", back_populates="reviews")


class InvestigationModel(Base):
    __tablename__ = "investigations"

    investigation_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    exception_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("exceptions.exception_id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    agent_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    most_likely_cause: Mapped[str] = mapped_column(String(255), default="UNKNOWN", nullable=False)
    findings: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    possible_causes: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
    evidence_collected: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    tools_used: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(255), default="Manual investigation required.", nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    exception_record = relationship("ExceptionModel", back_populates="investigations")


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    audit_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    match_status: Mapped[str] = mapped_column(String(50), nullable=False)
    exception_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    bank_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    ledger_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    difference: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    recommended_action: Mapped[str] = mapped_column(String(255), default="MANUAL_REVIEW", nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    reviewer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewer_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolution_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_history: Mapped[List[Any]] = mapped_column(JSON, default=list, nullable=False)
