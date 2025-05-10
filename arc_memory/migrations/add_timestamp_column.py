"""Migration script to add timestamp column to nodes table."""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from arc_memory.logging_conf import get_logger
from arc_memory.sql.db import get_connection
from arc_memory.utils.temporal import parse_timestamp, get_timestamp_str

logger = get_logger(__name__)


def migrate_database(db_path: Optional[Path] = None) -> bool:
    """Migrate the database to add the timestamp column.
    
    Args:
        db_path: Path to the database file. If None, uses the default path.
        
    Returns:
        True if migration was successful, False otherwise.
    """
    try:
        conn = get_connection(db_path)
        
        # Check if timestamp column exists
        cursor = conn.execute("PRAGMA table_info(nodes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "timestamp" not in columns:
            logger.info(f"Adding timestamp column to nodes table in {db_path}")
            
            # Add the timestamp column
            conn.execute("ALTER TABLE nodes ADD COLUMN timestamp TEXT")
            
            # Create index on timestamp column
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_timestamp ON nodes(timestamp)")
            
            # Update existing nodes with timestamps from extra field
            cursor = conn.execute("SELECT id, extra FROM nodes")
            updated_count = 0
            
            for row in cursor.fetchall():
                node_id, extra_json = row
                
                if extra_json:
                    try:
                        extra = json.loads(extra_json)
                        timestamp_str = None
                        
                        # Try to extract timestamp from extra
                        for key in ['created_at', 'timestamp', 'updated_at', 'merged_at', 'closed_at']:
                            if key in extra and extra[key]:
                                timestamp = parse_timestamp(extra[key])
                                if timestamp:
                                    timestamp_str = get_timestamp_str(timestamp)
                                    break
                        
                        if timestamp_str:
                            conn.execute(
                                "UPDATE nodes SET timestamp = ? WHERE id = ?",
                                (timestamp_str, node_id)
                            )
                            updated_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to extract timestamp for node {node_id}: {e}")
            
            conn.commit()
            logger.info(f"Successfully migrated database {db_path}: updated {updated_count} nodes with timestamps")
            return True
        else:
            logger.info(f"Database {db_path} already has timestamp column")
            return True
    except Exception as e:
        logger.error(f"Failed to migrate database {db_path}: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    # This allows running the migration script directly
    import sys
    
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
        success = migrate_database(db_path)
        sys.exit(0 if success else 1)
    else:
        success = migrate_database()
        sys.exit(0 if success else 1)
