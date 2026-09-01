"""Create the finance-controller persistence schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260901_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_dataset", sa.String(length=100), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("ingestion_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.UniqueConstraint("source_dataset", "source_record_id", name="uq_raw_source_record"),
    )
    op.create_index("ix_raw_transactions_source_dataset", "raw_transactions", ["source_dataset"])
    op.create_index("ix_raw_transactions_source_record_id", "raw_transactions", ["source_record_id"])

    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.String(length=100), primary_key=True),
        sa.Column("raw_transaction_id", sa.Integer(), sa.ForeignKey("raw_transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("reference_id", sa.String(length=100), nullable=True),
        sa.Column("customer_id", sa.String(length=100), nullable=True),
        sa.Column("order_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transactions_raw_transaction_id", "transactions", ["raw_transaction_id"])
    op.create_index("ix_transactions_reference_id", "transactions", ["reference_id"])

    for table in ("payment_records", "bank_records", "ledger_records"):
        extra_name = {"payment_records": "customer_id", "bank_records": "bank_name", "ledger_records": "account_code"}[table]
        extra_type = sa.String(length=100)
        columns = [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("transaction_id", sa.String(length=100), nullable=False),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("currency", sa.String(length=10), nullable=False),
            sa.Column("transaction_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("reference_id", sa.String(length=100), nullable=True),
        ]
        if table == "payment_records":
            columns.extend([sa.Column(extra_name, extra_type, nullable=True), sa.Column("order_id", sa.String(length=100), nullable=True)])
        elif table == "bank_records":
            columns.extend([sa.Column(extra_name, extra_type, nullable=True), sa.Column("account_id", sa.String(length=100), nullable=True)])
        else:
            columns.append(sa.Column(extra_name, extra_type, nullable=True))
        columns.extend([sa.Column("raw_payload", sa.JSON(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)])
        op.create_table(table, *columns)
        op.create_index(f"ix_{table}_transaction_id", table, ["transaction_id"])
        op.create_index(f"ix_{table}_reference_id", table, ["reference_id"])

    op.create_table(
        "audit_events",
        sa.Column("audit_id", sa.String(length=100), primary_key=True),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("match_status", sa.String(length=50), nullable=False),
        sa.Column("exception_type", sa.String(length=100), nullable=True),
        sa.Column("payment_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("bank_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("ledger_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("difference", sa.Numeric(18, 2), nullable=True),
        sa.Column("recommended_action", sa.String(length=255), nullable=False),
        sa.Column("review_status", sa.String(length=50), nullable=False),
        sa.Column("reviewer", sa.String(length=100), nullable=True),
        sa.Column("reviewer_comment", sa.Text(), nullable=True),
        sa.Column("processing_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_history", sa.JSON(), nullable=False),
    )
    op.create_index("ix_audit_events_transaction_id", "audit_events", ["transaction_id"])

    op.create_table(
        "exceptions",
        sa.Column("exception_id", sa.String(length=100), primary_key=True),
        sa.Column("audit_id", sa.String(length=100), nullable=False),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("exception_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("payment_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("bank_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("ledger_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("difference", sa.Numeric(18, 2), nullable=True),
        sa.Column("recommended_action", sa.String(length=255), nullable=False),
        sa.Column("review_status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("audit_id", "transaction_id", "review_status"):
        op.create_index(f"ix_exceptions_{column}", "exceptions", [column])

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("exception_id", sa.String(length=100), sa.ForeignKey("exceptions.exception_id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_state", sa.String(length=50), nullable=False),
        sa.Column("new_state", sa.String(length=50), nullable=False),
        sa.Column("reviewer", sa.String(length=100), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reviews_exception_id", "reviews", ["exception_id"])

    op.create_table(
        "investigations",
        sa.Column("investigation_id", sa.String(length=100), primary_key=True),
        sa.Column("exception_id", sa.String(length=100), sa.ForeignKey("exceptions.exception_id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("agent_status", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("most_likely_cause", sa.String(length=255), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("possible_causes", sa.JSON(), nullable=False),
        sa.Column("evidence_collected", sa.JSON(), nullable=False),
        sa.Column("tools_used", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.String(length=255), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_investigations_exception_id", "investigations", ["exception_id"])
    op.create_index("ix_investigations_transaction_id", "investigations", ["transaction_id"])


def downgrade() -> None:
    for table in ("investigations", "reviews", "exceptions", "audit_events", "ledger_records", "bank_records", "payment_records", "transactions", "raw_transactions"):
        op.drop_table(table)
