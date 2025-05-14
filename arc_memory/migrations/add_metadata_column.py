"""Migration script to add metadata column to refresh_timestamps table.

This migration adds a metadata column to the refresh_timestamps table,
which is used to store information needed for incremental updates.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from arc_memory.logging_conf import get_logger
from arc_memory.sql.db import get_connection, get_db_path

logger = get_logger(__name__)


def run_migration(db_path: Optional[Path] = None) -> bool:
    """Run the migration to add the metadata column to refresh_timestamps table.

    Args:
        db_path: Path to the database file. If None, uses the default path.

    Returns:
        True if the migration was successful, False otherwise.
    """
    if db_path is None:
        db_path = get_db_path()

    logger.info(f"Running migration to add metadata column to refresh_timestamps table in {db_path}")

    try:
        # Connect to the database
        conn = get_connection(db_path, check_exists=True)
        cursor = conn.cursor()

        # Check if the refresh_timestamps table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='refresh_timestamps'")
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            # Create the table with all columns
            logger.info("refresh_timestamps table does not exist, creating it")
            cursor.execute("""
                CREATE TABLE refresh_timestamps (
                    source TEXT PRIMARY KEY,
                    timestamp TEXT,
                    metadata TEXT
                )
            """)
            conn.commit()
            logger.info("Created refresh_timestamps table with metadata column")
            conn.close()
            return True

        # Check if the metadata column exists
        try:
            cursor.execute("SELECT metadata FROM refresh_timestamps LIMIT 1")
            # If we get here, the column exists
            logger.info("metadata column already exists in refresh_timestamps table")
            conn.close()
            return True
        except sqlite3.OperationalError:
            # Metadata column doesn't exist, add it
            logger.info("Adding metadata column to refresh_timestamps table")
            cursor.execute("ALTER TABLE refresh_timestamps ADD COLUMN metadata TEXT")
            conn.commit()
            logger.info("Added metadata column to refresh_timestamps table")
            conn.close()
            return True

    except Exception as e:
        logger.error(f"Failed to run migration: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("Migration completed successfully")
    else:
        print("Migration failed")
