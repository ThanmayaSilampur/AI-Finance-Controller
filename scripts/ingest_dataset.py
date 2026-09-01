#!/usr/bin/env python3
"""CLI script for ingesting external financial datasets into the AI Finance Controller database.

Preserves full data provenance, enforces raw lineage, and maps to normalized entities.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import sessionmaker

# Ensure parent directory is on sys.path when running from command line
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.adapter import DataAdapter
from app.db.repository import DatabaseRepository
from app.db.session import SessionFactory, create_db_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dataset_ingestion")


REQUIRED_IBM_FIELDS = {"Timestamp", "Amount Paid"}
FALLBACK_REQUIRED_FIELDS = {"transaction_id", "amount"}


def validate_header(header: list[str]) -> bool:
    """Validate that the CSV header contains required minimum fields."""
    header_set = set(header)
    if REQUIRED_IBM_FIELDS.issubset(header_set):
        return True
    if any(f in header_set for f in FALLBACK_REQUIRED_FIELDS):
        return True
    return False


def ingest_file(
    file_path: str | Path,
    dataset_name: str = "IBM_AML_DATA",
    db_session=None,
) -> Dict[str, Any]:
    """Ingest external financial CSV dataset line-by-line into PostgreSQL / SQLite database."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    stats = {
        "file": str(path),
        "dataset_name": dataset_name,
        "read": 0,
        "accepted": 0,
        "rejected": 0,
        "skipped_duplicates": 0,
        "errors": [],
    }

    session_created = False
    if db_session is None:
        db_session = SessionFactory()
        session_created = True

    repo = DatabaseRepository(db_session)

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not validate_header(reader.fieldnames):
                err_msg = f"Invalid CSV header in {path}. Headers found: {reader.fieldnames}"
                logger.error(err_msg)
                stats["errors"].append(err_msg)
                stats["rejected"] += 1
                return stats

            for index, row in enumerate(reader, start=1):
                stats["read"] += 1
                try:
                    source_record_id = DataAdapter.extract_source_record_id(row, index)

                    # Save raw transaction
                    raw_model = repo.save_raw_transaction(
                        source_dataset=dataset_name,
                        source_record_id=source_record_id,
                        raw_payload=dict(row),
                        status="INGESTED",
                    )

                    # Check if normalized record already exists (idempotency)
                    norm_txn = DataAdapter.raw_to_normalized_transaction(
                        source_record_id=source_record_id,
                        raw_payload=dict(row),
                        source_dataset=dataset_name,
                        raw_db_id=raw_model.id,
                    )

                    existing_norm = repo.get_transaction(norm_txn.transaction_id)
                    if existing_norm:
                        stats["skipped_duplicates"] += 1
                        continue

                    # Save normalized transaction
                    repo.save_normalized_transaction(norm_txn, raw_transaction_id=raw_model.id)

                    # Project and save to 3-way reconciliation streams
                    payments, banks, ledgers = DataAdapter.project_to_three_way_streams([norm_txn])
                    for p in payments:
                        repo.save_payment_record(p)
                    for b in banks:
                        repo.save_bank_record(b)
                    for l in ledgers:
                        repo.save_ledger_record(l)

                    stats["accepted"] += 1

                except Exception as exc:
                    logger.error(f"Error processing record #{index} (row: {row}): {exc}")
                    stats["rejected"] += 1
                    stats["errors"].append(f"Record #{index}: {exc}")

    finally:
        if session_created:
            db_session.close()

    logger.info(
        f"Ingestion complete for {path}. Read: {stats['read']}, Accepted: {stats['accepted']}, "
        f"Duplicates Skipped: {stats['skipped_duplicates']}, Rejected: {stats['rejected']}"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(description="Ingest external financial dataset into AI Finance Controller database.")
    parser.add_argument("--file", "-f", required=True, help="Path to external CSV dataset file.")
    parser.add_argument("--dataset-name", "-d", default="IBM_AML_DATA", help="Source dataset name indicator.")
    parser.add_argument("--db-url", help="Optional override for DATABASE_URL environment variable.")

    args = parser.parse_args()

    if args.db_url:
        target_engine = create_db_engine(args.db_url)
        session_factory = sessionmaker(bind=target_engine)
        session = session_factory()
    else:
        session = None

    try:
        stats = ingest_file(args.file, dataset_name=args.dataset_name, db_session=session)
        print("\n--- INGESTION SUMMARY ---")
        print(f"File:               {stats['file']}")
        print(f"Dataset Name:       {stats['dataset_name']}")
        print(f"Records Read:       {stats['read']}")
        print(f"Records Accepted:   {stats['accepted']}")
        print(f"Duplicates Skipped: {stats['skipped_duplicates']}")
        print(f"Records Rejected:   {stats['rejected']}")
        if stats["errors"]:
            print(f"\nErrors encountered ({len(stats['errors'])}):")
            for err in stats["errors"][:5]:
                print(f"  - {err}")
        if stats["rejected"] > 0 and stats["accepted"] == 0:
            sys.exit(1)
    except Exception as exc:
        logger.error(f"Fatal error during dataset ingestion: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
