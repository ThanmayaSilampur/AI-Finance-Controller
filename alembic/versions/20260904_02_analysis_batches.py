"""Add analysis_batches table and batch_id columns.

Revision ID: 20260904_02
Revises: 20260901_01
Create Date: 2026-09-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260904_02"
down_revision = "20260901_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create analysis_batches table
    op.create_table(
        "analysis_batches",
        sa.Column("batch_id", sa.String(length=100), primary_key=True),
        sa.Column("batch_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="COMPLETED"),
        sa.Column("payment_filename", sa.String(length=255), nullable=True),
        sa.Column("bank_filename", sa.String(length=255), nullable=True),
        sa.Column("ledger_filename", sa.String(length=255), nullable=True),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exception_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("match_rate", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("processing_duration_ms", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("throughput_rps", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("exception_breakdown", sa.JSON(), nullable=False),
        sa.Column("summary_metadata", sa.JSON(), nullable=False),
    )

    # 2. Add batch_id column, foreign keys, and indices to dependent tables
    tables = [
        "transactions",
        "payment_records",
        "bank_records",
        "ledger_records",
        "exceptions",
        "audit_events",
    ]
    for table_name in tables:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column("batch_id", sa.String(length=100), nullable=True)
            )
            batch_op.create_foreign_key(
                f"fk_{table_name}_batch_id",
                "analysis_batches",
                ["batch_id"],
                ["batch_id"],
                ondelete="CASCADE",
            )
            batch_op.create_index(
                f"ix_{table_name}_batch_id",
                ["batch_id"],
            )


def downgrade() -> None:
    tables = [
        "audit_events",
        "exceptions",
        "ledger_records",
        "bank_records",
        "payment_records",
        "transactions",
    ]
    for table_name in tables:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_batch_id")
            batch_op.drop_constraint(f"fk_{table_name}_batch_id", type_="foreignkey")
            batch_op.drop_column("batch_id")

    op.drop_table("analysis_batches")
