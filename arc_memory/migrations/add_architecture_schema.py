"""Migration script to add architecture schema support to the database.

This migration ensures that the database schema supports the repository identity
and architecture schema features, including the repositories table and the
necessary columns in the nodes table.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def migrate_database(db_path: Any) -> bool:
    """Migrate the database to support architecture schema.

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

        # Begin transaction
        conn.execute("BEGIN TRANSACTION")

        # Check if the repositories table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repositories'")
        if not cursor.fetchone():
            logger.info(f"Creating repositories table in {db_path}")
            conn.execute("""
                CREATE TABLE repositories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT,
                    local_path TEXT NOT NULL,
                    default_branch TEXT DEFAULT 'main',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
        else:
            logger.info(f"repositories table already exists in {db_path}")

        # Check if the repo_id column exists in the nodes table
        cursor = conn.execute("PRAGMA table_info(nodes)")
        columns = [row["name"] for row in cursor.fetchall()]
        
        # Add repo_id column if it doesn't exist
        if "repo_id" not in columns:
            logger.info(f"Adding repo_id column to nodes table in {db_path}")
            conn.execute("ALTER TABLE nodes ADD COLUMN repo_id TEXT")
            
            # Create index on repo_id column
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_repo_id ON nodes(repo_id)")
        else:
            logger.info(f"repo_id column already exists in nodes table in {db_path}")

        # Commit transaction
        conn.execute("COMMIT")
        conn.close()

        logger.info(f"Successfully migrated database {db_path} to support architecture schema")
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
        print("Usage: python -m arc_memory.migrations.add_architecture_schema <db_path>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    success = migrate_database(db_path)
    if success:
        print(f"Successfully migrated database {db_path}")
    else:
        print(f"Failed to migrate database {db_path}")
        sys.exit(1)
