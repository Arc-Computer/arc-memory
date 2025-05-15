"""Migration script to add repo_id column to nodes table.

This migration adds the repo_id column to the nodes table in existing databases.
It also creates the repositories table if it doesn't exist.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def migrate_database(db_path: Any) -> bool:
    """Migrate the database to add repo_id column to nodes table.

    Args:
        db_path: Path to the database file.

    Returns:
        True if migration was successful, False otherwise.
    """
    try:
        # Convert to Path if it's a string
        if isinstance(db_path, str):
            db_path = Path(db_path)

        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Check if the repo_id column already exists in the nodes table
        cursor = conn.execute("PRAGMA table_info(nodes)")
        columns = [row["name"] for row in cursor.fetchall()]

        # Begin transaction
        conn.execute("BEGIN TRANSACTION")

        # Add repo_id column if it doesn't exist
        if "repo_id" not in columns:
            logger.info(f"Adding repo_id column to nodes table in {db_path}")
            conn.execute("ALTER TABLE nodes ADD COLUMN repo_id TEXT")
        else:
            logger.info(f"repo_id column already exists in nodes table in {db_path}")

        # Create repositories table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT,
                local_path TEXT NOT NULL,
                default_branch TEXT DEFAULT 'main',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Create index on repo_id column if it doesn't exist
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_nodes_repo_id ON nodes(repo_id)
        """)

        # Commit transaction
        conn.execute("COMMIT")
        conn.close()

        logger.info(f"Successfully migrated database {db_path} to add repo_id column")
        return True
    except Exception as e:
        logger.error(f"Failed to migrate database {db_path}: {e}")
        try:
            conn.execute("ROLLBACK")
            conn.close()
        except Exception:
            pass
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python -m arc_memory.migrations.add_repo_id_column <db_path>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    success = migrate_database(db_path)
    if success:
        print(f"Successfully migrated database {db_path}")
    else:
        print(f"Failed to migrate database {db_path}")
        sys.exit(1)
