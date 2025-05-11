"""Core auto-refresh functionality for Arc Memory.

This module provides the core functionality for automatically refreshing the knowledge graph
with the latest data from various sources.
"""

from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from arc_memory.db import get_adapter
from arc_memory.db.metadata import (
    get_refresh_timestamp,
    get_all_refresh_timestamps,
)
from arc_memory.errors import AutoRefreshError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def check_refresh_needed(
    source: str,
    min_interval: Optional[timedelta] = None,
    adapter_type: Optional[str] = None
) -> Tuple[bool, Optional[datetime]]:
    """Check if a source needs refreshing.

    Args:
        source: The source name (e.g., 'github', 'linear').
        min_interval: The minimum interval between refreshes. If None, defaults to 1 hour.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        A tuple of (needs_refresh, last_refresh_time), where needs_refresh is a boolean
        indicating whether the source needs refreshing, and last_refresh_time is the
        timestamp of the last refresh, or None if the source has never been refreshed.

    Raises:
        AutoRefreshError: If checking refresh status fails.
    """
    if min_interval is None:
        min_interval = timedelta(hours=1)

    try:
        last_refresh = get_refresh_timestamp(source, adapter_type)

        if last_refresh is None:
            # Source has never been refreshed
            logger.info(f"Source '{source}' has never been refreshed, refresh needed")
            return True, None

        now = datetime.now()
        time_since_refresh = now - last_refresh

        needs_refresh = time_since_refresh >= min_interval

        if needs_refresh:
            logger.info(
                f"Source '{source}' needs refreshing "
                f"(last refresh: {last_refresh.isoformat()}, "
                f"interval: {time_since_refresh})"
            )
        else:
            logger.debug(
                f"Source '{source}' does not need refreshing "
                f"(last refresh: {last_refresh.isoformat()}, "
                f"interval: {time_since_refresh})"
            )

        return needs_refresh, last_refresh
    except Exception as e:
        error_msg = f"Failed to check refresh status for source '{source}': {e}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "source": source,
                "min_interval": str(min_interval),
                "error": str(e),
            }
        )


def get_sources_needing_refresh(
    sources: Optional[List[str]] = None,
    min_interval: Optional[timedelta] = None,
    adapter_type: Optional[str] = None
) -> Dict[str, Optional[datetime]]:
    """Get a list of sources that need refreshing.

    Args:
        sources: A list of source names to check. If None, checks all known sources.
        min_interval: The minimum interval between refreshes. If None, defaults to 1 hour.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        A dictionary mapping source names to their last refresh timestamps (or None if never refreshed)
        for sources that need refreshing.

    Raises:
        AutoRefreshError: If checking refresh status fails.
    """
    if min_interval is None:
        min_interval = timedelta(hours=1)

    try:
        # If no sources specified, check all known sources
        if sources is None:
            # Get all sources that have been refreshed before
            all_timestamps = get_all_refresh_timestamps(adapter_type)
            sources = list(all_timestamps.keys())

            # Add default sources if they're not already in the list
            default_sources = ["github", "linear", "adr"]
            for source in default_sources:
                if source not in sources:
                    sources.append(source)

        sources_to_refresh = {}
        for source in sources:
            needs_refresh, last_refresh = check_refresh_needed(source, min_interval, adapter_type)
            if needs_refresh:
                sources_to_refresh[source] = last_refresh

        return sources_to_refresh
    except Exception as e:
        error_msg = f"Failed to get sources needing refresh: {e}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "sources": sources,
                "min_interval": str(min_interval),
                "error": str(e),
            }
        )


def refresh_source(
    source: str,
    force: bool = False,
    min_interval: Optional[timedelta] = None,
    adapter_type: Optional[str] = None
) -> bool:
    """Refresh a specific source.

    Args:
        source: The source name (e.g., 'github', 'linear').
        force: Whether to force a refresh even if the minimum interval hasn't elapsed.
        min_interval: The minimum interval between refreshes. If None, defaults to 1 hour.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        True if the source was refreshed, False otherwise.

    Raises:
        AutoRefreshError: If refreshing the source fails.
    """
    # Get the database adapter
    adapter = get_adapter(adapter_type)
    if not adapter.is_connected():
        from arc_memory.sql.db import get_db_path
        db_path = get_db_path()
        adapter.connect({"db_path": str(db_path)})
        adapter.init_db()

    try:
        # Check if refresh is needed
        if not force:
            needs_refresh, last_refresh = check_refresh_needed(source, min_interval, adapter_type)
            if not needs_refresh:
                logger.info(f"Skipping refresh for source '{source}' (last refresh: {last_refresh.isoformat() if last_refresh else 'never'})")
                return False

        # Import the source-specific refresh module dynamically
        import importlib
        try:
            module_name = f"arc_memory.auto_refresh.sources.{source}"
            module = importlib.import_module(module_name)
            refresh_func = getattr(module, "refresh")
        except (ImportError, AttributeError) as e:
            error_msg = f"Source '{source}' is not supported for auto-refresh: {e}"
            logger.error(error_msg)
            # Raise the exception to prevent further execution
            raise AutoRefreshError(
                error_msg,
                details={
                    "source": source,
                    "error": str(e),
                }
            )

        # Call the source-specific refresh function with the adapter
        logger.info(f"Refreshing source '{source}'")
        refresh_func(adapter)

        # Update the refresh timestamp directly using the adapter
        now = datetime.now()
        try:
            adapter.save_refresh_timestamp(source, now)
            logger.info(f"Successfully refreshed source '{source}' at {now.isoformat()}")
        except Exception as e:
            error_msg = f"Failed to save refresh timestamp for {source}: {e}"
            logger.error(error_msg)
            raise AutoRefreshError(
                error_msg,
                details={
                    "source": source,
                    "timestamp": now.isoformat(),
                    "error": str(e),
                }
            )

        return True
    except Exception as e:
        error_msg = f"Failed to refresh source '{source}': {e}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "source": source,
                "force": force,
                "min_interval": str(min_interval) if min_interval else None,
                "error": str(e),
            }
        )


def refresh_all_sources(
    sources: Optional[List[str]] = None,
    force: bool = False,
    min_interval: Optional[timedelta] = None,
    adapter_type: Optional[str] = None
) -> Dict[str, bool]:
    """Refresh all specified sources.

    Args:
        sources: A list of source names to refresh. If None, refreshes all known sources.
        force: Whether to force a refresh even if the minimum interval hasn't elapsed.
        min_interval: The minimum interval between refreshes. If None, defaults to 1 hour.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        A dictionary mapping source names to booleans indicating whether they were refreshed.

    Raises:
        AutoRefreshError: If refreshing any source fails.
    """
    if force:
        # If forcing refresh, use the provided sources or default ones
        sources_to_refresh = sources or ["github", "linear", "adr"]
    else:
        # Otherwise, get only the sources that need refreshing
        sources_needing_refresh = get_sources_needing_refresh(sources, min_interval, adapter_type)
        sources_to_refresh = list(sources_needing_refresh.keys())

    results = {}
    errors = []

    for source in sources_to_refresh:
        try:
            refreshed = refresh_source(source, force, min_interval, adapter_type)
            results[source] = refreshed
        except Exception as e:
            logger.error(f"Error refreshing source '{source}': {e}")
            results[source] = False
            errors.append((source, str(e)))

    if errors:
        error_details = {source: error for source, error in errors}
        error_msg = f"Failed to refresh {len(errors)} sources: {', '.join(source for source, _ in errors)}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "errors": error_details,
                "results": results,
            }
        )

    return results
