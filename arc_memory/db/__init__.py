"""Database abstraction layer for Arc Memory.

This package provides a database abstraction layer for Arc Memory, allowing it to work
with different database backends (SQLite, Neo4j).
"""

from arc_memory.db.base import DatabaseAdapter
from arc_memory.db.sqlite_adapter import SQLiteAdapter
from arc_memory.db.neo4j_adapter import Neo4jAdapter
from arc_memory.config import get_config

def get_adapter(adapter_type: str = None) -> DatabaseAdapter:
    """Get a database adapter instance.
    
    Args:
        adapter_type: The type of adapter to get. If None, uses the configured adapter.
    
    Returns:
        A database adapter instance.
    
    Raises:
        ValueError: If the adapter type is not supported.
    """
    if adapter_type is None:
        # Get the adapter type from the configuration
        config = get_config()
        adapter_type = config.get("database", {}).get("adapter", "sqlite")
    
    if adapter_type == "sqlite":
        return SQLiteAdapter()
    elif adapter_type == "neo4j":
        return Neo4jAdapter()
    else:
        raise ValueError(f"Unsupported adapter type: {adapter_type}")
