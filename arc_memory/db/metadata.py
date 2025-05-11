"""Metadata utilities for Arc Memory.

This module provides utility functions for working with metadata and refresh timestamps
in the Arc Memory database.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from arc_memory.db import get_adapter
from arc_memory.errors import DatabaseError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


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
    # This is a convenience function that retrieves all refresh timestamps
    # from the metadata table. It's not directly supported by the adapter interface,
    # so we implement it here using the adapter's get_all_metadata method.
    adapter = get_adapter(adapter_type)
    
    try:
        # For SQLite, we can query the refresh_timestamps table directly
        if adapter.get_name() == "sqlite":
            if not adapter.is_connected():
                raise DatabaseError("Not connected to database")
                
            cursor = adapter.conn.execute(
                """
                SELECT source, timestamp
                FROM refresh_timestamps
                """
            )
            timestamps = {}
            for row in cursor:
                timestamps[row[0]] = datetime.fromisoformat(row[1])
            return timestamps
        else:
            # For other adapters, we'll need to implement this differently
            # or add a method to the adapter interface
            logger.warning(f"get_all_refresh_timestamps not fully implemented for {adapter.get_name()} adapter")
            return {}
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
