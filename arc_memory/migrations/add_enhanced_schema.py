"""Migration script to add enhanced schema fields to the database.

This migration is part of the enhanced schema PR.

This migration adds the following fields to the nodes table:
- created_at: When the node was first created
- updated_at: When the node was last updated
- valid_from: When this version became valid
- valid_until: When this version became invalid
- metadata: Enhanced metadata (renamed from extra)
- embedding: Vector embedding for semantic search
- url: URL to the resource (if applicable)

It also adds indices for these fields to improve query performance.
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def migrate_database(db_path: str) -> bool:
    """Migrate the database to add enhanced schema fields.

    Args:
        db_path: Path to the database file.

    Returns:
        True if migration was successful, False otherwise.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check if migration is needed
        cursor.execute("PRAGMA table_info(nodes)")
        columns = {row["name"] for row in cursor.fetchall()}

        # Check if all new columns already exist
        new_columns = {
            "created_at", "updated_at", "valid_from", "valid_until",
            "metadata", "embedding", "url"
        }

        if new_columns.issubset(columns):
            logger.info(f"Enhanced schema migration already applied to {db_path}")
            conn.close()
            return True

        # Begin transaction
        conn.execute("BEGIN TRANSACTION")

        # Add new columns if they don't exist
        for column in new_columns:
            if column not in columns:
                column_type = "BLOB" if column == "embedding" else "TEXT"
                try:
                    conn.execute(f"ALTER TABLE nodes ADD COLUMN {column} {column_type}")
                    logger.info(f"Added column {column} to nodes table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        logger.info(f"Column {column} already exists in nodes table")
                    else:
                        raise

        # Create indices for new columns
        index_columns = {
            "created_at", "updated_at", "valid_from", "valid_until", "url"
        }

        for column in index_columns:
            if column in new_columns:
                try:
                    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_nodes_{column} ON nodes({column})")
                    logger.info(f"Created index idx_nodes_{column} on nodes table")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Failed to create index for {column}: {e}")

        # Migrate data from extra to metadata if needed
        if "metadata" in new_columns and "extra" in columns:
            try:
                # Copy data from extra to metadata for all rows where metadata is NULL
                conn.execute("""
                UPDATE nodes
                SET metadata = extra
                WHERE metadata IS NULL AND extra IS NOT NULL
                """)
                logger.info("Migrated data from extra to metadata")
            except sqlite3.OperationalError as e:
                logger.warning(f"Failed to migrate data from extra to metadata: {e}")

        # Set created_at and updated_at based on timestamp if available
        if "created_at" in new_columns and "timestamp" in columns:
            try:
                conn.execute("""
                UPDATE nodes
                SET created_at = timestamp
                WHERE created_at IS NULL AND timestamp IS NOT NULL
                """)
                logger.info("Set created_at based on timestamp")
            except sqlite3.OperationalError as e:
                logger.warning(f"Failed to set created_at based on timestamp: {e}")

        if "updated_at" in new_columns and "timestamp" in columns:
            try:
                conn.execute("""
                UPDATE nodes
                SET updated_at = timestamp
                WHERE updated_at IS NULL AND timestamp IS NOT NULL
                """)
                logger.info("Set updated_at based on timestamp")
            except sqlite3.OperationalError as e:
                logger.warning(f"Failed to set updated_at based on timestamp: {e}")

        # Set valid_from to created_at if available
        if "valid_from" in new_columns and "created_at" in columns:
            try:
                conn.execute("""
                UPDATE nodes
                SET valid_from = created_at
                WHERE valid_from IS NULL AND created_at IS NOT NULL
                """)
                logger.info("Set valid_from based on created_at")
            except sqlite3.OperationalError as e:
                logger.warning(f"Failed to set valid_from based on created_at: {e}")

        # Commit transaction
        conn.execute("COMMIT")
        conn.close()

        logger.info(f"Successfully applied enhanced schema migration to {db_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to apply enhanced schema migration to {db_path}: {e}")
        try:
            conn.execute("ROLLBACK")
            conn.close()
        except Exception:
            pass
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <db_path>")
        sys.exit(1)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    db_path = sys.argv[1]
    success = migrate_database(db_path)

    if success:
        print(f"Successfully applied enhanced schema migration to {db_path}")
        sys.exit(0)
    else:
        print(f"Failed to apply enhanced schema migration to {db_path}")
        sys.exit(1)
