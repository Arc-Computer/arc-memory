"""Metadata utilities for Arc Memory.

This module provides utility functions for working with metadata and refresh timestamps
in the Arc Memory database.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from arc_memory.db import get_adapter
from arc_memory.errors import DatabaseError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def ensure_adapter_connected(adapter):
    """Ensure the adapter is connected to the database.

    Args:
        adapter: The database adapter to check and connect if needed.
    """
    if not adapter.is_connected():
        from arc_memory.sql.db import get_db_path
        db_path = get_db_path()
        adapter.connect({"db_path": str(db_path)})
        # Initialize the database schema to ensure tables exist
        adapter.init_db()


def save_refresh_timestamp(source: str, timestamp: datetime, adapter_type: Optional[str] = None) -> None:
    """Save the last refresh timestamp for a source.

    Args:
        source: The source name (e.g., 'github', 'linear').
        timestamp: The timestamp of the last refresh.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Raises:
        DatabaseError: If saving the timestamp fails.
    """
    adapter = get_adapter(adapter_type)

    # Ensure the adapter is connected
    ensure_adapter_connected(adapter)

    try:
        adapter.save_refresh_timestamp(source, timestamp)
        logger.info(f"Saved refresh timestamp for {source}: {timestamp.isoformat()}")
    except Exception as e:
        error_msg = f"Failed to save refresh timestamp for {source}: {e}"
        logger.error(error_msg)
        raise DatabaseError(
            error_msg,
            details={
                "source": source,
                "timestamp": timestamp.isoformat(),
                "error": str(e),
            }
        )


def get_refresh_timestamp(source: str, adapter_type: Optional[str] = None) -> Optional[datetime]:
    """Get the last refresh timestamp for a source.

    Args:
        source: The source name (e.g., 'github', 'linear').
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        The timestamp of the last refresh, or None if not found.

    Raises:
        DatabaseError: If getting the timestamp fails.
    """
    adapter = get_adapter(adapter_type)

    # Ensure the adapter is connected
    ensure_adapter_connected(adapter)

    try:
        timestamp = adapter.get_refresh_timestamp(source)
        if timestamp:
            logger.debug(f"Retrieved refresh timestamp for {source}: {timestamp.isoformat()}")
        else:
            logger.debug(f"No refresh timestamp found for {source}")
        return timestamp
    except Exception as e:
        error_msg = f"Failed to get refresh timestamp for {source}: {e}"
        logger.error(error_msg)
        raise DatabaseError(
            error_msg,
            details={
                "source": source,
                "error": str(e),
            }
        )


def get_all_refresh_timestamps(adapter_type: Optional[str] = None) -> Dict[str, datetime]:
    """Get all refresh timestamps.

    Args:
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        A dictionary mapping source names to refresh timestamps.

    Raises:
        DatabaseError: If getting the timestamps fails.
    """
    adapter = get_adapter(adapter_type)

    # Ensure the adapter is connected
    ensure_adapter_connected(adapter)

    try:
        # Use the adapter's get_all_refresh_timestamps method
        return adapter.get_all_refresh_timestamps()
    except Exception as e:
        error_msg = f"Failed to get all refresh timestamps: {e}"
        logger.error(error_msg)
        raise DatabaseError(
            error_msg,
            details={
                "error": str(e),
            }
        )


def save_metadata(key: str, value: Any, adapter_type: Optional[str] = None) -> None:
    """Save metadata to the database.

    Args:
        key: The metadata key.
        value: The metadata value.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Raises:
        DatabaseError: If saving the metadata fails.
    """
    adapter = get_adapter(adapter_type)

    try:
        adapter.save_metadata(key, value)
        logger.info(f"Saved metadata for {key}")
    except Exception as e:
        error_msg = f"Failed to save metadata for {key}: {e}"
        logger.error(error_msg)
        raise DatabaseError(
            error_msg,
            details={
                "key": key,
                "error": str(e),
            }
        )


def get_metadata(key: str, default: Any = None, adapter_type: Optional[str] = None) -> Any:
    """Get metadata from the database.

    Args:
        key: The metadata key.
        default: The default value to return if the key doesn't exist.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        The metadata value, or the default if not found.

    Raises:
        DatabaseError: If getting the metadata fails.
    """
    adapter = get_adapter(adapter_type)

    try:
        value = adapter.get_metadata(key, default)
        logger.debug(f"Retrieved metadata for {key}")
        return value
    except Exception as e:
        error_msg = f"Failed to get metadata for {key}: {e}"
        logger.error(error_msg)
        raise DatabaseError(
            error_msg,
            details={
                "key": key,
                "error": str(e),
            }
        )


def get_all_metadata(adapter_type: Optional[str] = None) -> Dict[str, Any]:
    """Get all metadata from the database.

    Args:
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        A dictionary of all metadata.

    Raises:
        DatabaseError: If getting the metadata fails.
    """
    adapter = get_adapter(adapter_type)

    try:
        metadata = adapter.get_all_metadata()
        logger.debug(f"Retrieved all metadata ({len(metadata)} keys)")
        return metadata
    except Exception as e:
        error_msg = f"Failed to get all metadata: {e}"
        logger.error(error_msg)
        raise DatabaseError(
            error_msg,
            details={
                "error": str(e),
            }
        )
