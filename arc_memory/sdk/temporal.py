"""Temporal Analysis API for Arc Memory SDK.

This module provides methods for analyzing the history of entities over time.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from arc_memory.db.base import DatabaseAdapter
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import NodeType
from arc_memory.sdk.cache import cached
from arc_memory.sdk.errors import QueryError
from arc_memory.sdk.models import HistoryEntry
from arc_memory.sdk.progress import ProgressCallback, ProgressStage

logger = get_logger(__name__)


@cached()
def get_entity_history(
    adapter: DatabaseAdapter,
    entity_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_related: bool = False,
    callback: Optional[ProgressCallback] = None
) -> List[HistoryEntry]:
    """Get the history of an entity over time.

    This method retrieves the history of an entity, showing how it has changed
    over time and how it has been referenced by other entities.

    Args:
        adapter: The database adapter to use.
        entity_id: The ID of the entity.
        start_date: Optional start date for the history.
        end_date: Optional end date for the history.
        include_related: Whether to include related entities in the history.
        callback: Optional callback for progress reporting.

    Returns:
        A list of HistoryEntry objects representing the entity's history.

    Raises:
        QueryError: If getting the entity history fails.
    """
    try:
        # Report progress
        if callback:
            callback(
                ProgressStage.INITIALIZING,
                "Initializing entity history analysis",
                0.0
            )

        # Get the entity
        entity = adapter.get_node_by_id(entity_id)
        if not entity:
            raise QueryError(f"Entity not found: {entity_id}")

        # Report progress
        if callback:
            callback(
                ProgressStage.QUERYING,
                "Querying entity history",
                0.2
            )

        # Get references to the entity
        references = _get_entity_references(adapter, entity_id)

        # Filter by date range if specified
        if start_date or end_date:
            references = _filter_by_date_range(references, start_date, end_date)

        # Report progress
        if callback:
            callback(
                ProgressStage.PROCESSING,
                "Processing entity history",
                0.6
            )

        # Get related entities if requested
        if include_related:
            references = _include_related_entities(adapter, references)

        # Report progress
        if callback:
            callback(
                ProgressStage.COMPLETING,
                "Entity history analysis complete",
                1.0
            )

        # Convert to HistoryEntry models
        history_entries = []
        for ref in references:
            entry = HistoryEntry(
                id=ref["id"],
                type=ref["type"],
                title=ref.get("title"),
                body=ref.get("body"),
                timestamp=ref.get("timestamp"),
                properties=ref.get("properties", {}),
                related_entities=[],
                change_type=ref.get("change_type", "referenced"),
                previous_version=ref.get("previous_version")
            )
            history_entries.append(entry)

        return history_entries

    except Exception as e:
        logger.exception(f"Error in get_entity_history: {e}")
        raise QueryError(f"Failed to get entity history: {e}")


def _get_entity_references(adapter: DatabaseAdapter, entity_id: str) -> List[Dict[str, Any]]:
    """Get references to an entity.

    This function retrieves all references to an entity, including direct modifications
    and mentions in other entities.

    Args:
        adapter: The database adapter to use.
        entity_id: The ID of the entity.

    Returns:
        A list of dictionaries representing references to the entity.
    """
    # This is a simplified implementation that would be enhanced in a real system
    references = []

    # Get incoming edges (entities that reference this entity)
    incoming_edges = adapter.get_edges_by_dst(entity_id)
    for edge in incoming_edges:
        source = adapter.get_node_by_id(edge["src"])
        if source:
            # Add the source entity as a reference
            reference = {
                "id": source["id"],
                "type": source["type"],
                "title": source.get("title"),
                "body": source.get("body"),
                "timestamp": source.get("timestamp"),
                "properties": source.get("extra", {}),
                "change_type": _determine_change_type(edge["rel"]),
                "previous_version": None
            }
            references.append(reference)

    # Sort references by timestamp (newest first)
    references.sort(
        key=lambda r: r.get("timestamp", ""),
        reverse=True
    )

    return references


def _determine_change_type(relationship: str) -> str:
    """Determine the change type based on the relationship.

    Args:
        relationship: The relationship type.

    Returns:
        The change type (created, modified, referenced).
    """
    # Map relationship types to change types
    change_type_map = {
        "MODIFIES": "modified",
        "CREATES": "created",
        "MENTIONS": "referenced",
        "MERGES": "merged",
        "DEPENDS_ON": "depends_on",
        "IMPLEMENTS": "implements",
        "DECIDES": "decides"
    }
    return change_type_map.get(relationship, "referenced")


def _filter_by_date_range(
    references: List[Dict[str, Any]],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Filter references by date range.

    Args:
        references: The references to filter.
        start_date: Optional start date for the filter.
        end_date: Optional end date for the filter.

    Returns:
        Filtered references.
    """
    if not start_date and not end_date:
        return references

    filtered = []
    for ref in references:
        timestamp = ref.get("timestamp")
        if not timestamp:
            continue

        # Convert timestamp to datetime if it's a string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                continue

        # Check if the timestamp is within the date range
        if start_date and timestamp < start_date:
            continue
        if end_date and timestamp > end_date:
            continue

        filtered.append(ref)

    return filtered


def _include_related_entities(
    adapter: DatabaseAdapter, references: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Include related entities in the references.

    This function adds related entities to the references, such as PRs that
    mention the same issues, or commits that modify the same files.

    Args:
        adapter: The database adapter to use.
        references: The references to enhance.

    Returns:
        Enhanced references with related entities.
    """
    # This is a simplified implementation that would be enhanced in a real system
    # In a real implementation, we would analyze the references to find related
    # entities and add them to the result
    return references
