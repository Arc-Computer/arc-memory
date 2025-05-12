"""Entity Relationship API for Arc Memory SDK.

This module provides methods for exploring relationships between entities
in the knowledge graph.
"""

from typing import Any, Dict, List, Optional, Union

from arc_memory.db.base import DatabaseAdapter
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import EdgeRel, NodeType
from arc_memory.sdk.cache import cached
from arc_memory.sdk.errors import QueryError
from arc_memory.sdk.models import EntityDetails, RelatedEntity
from arc_memory.sdk.progress import ProgressCallback, ProgressStage

logger = get_logger(__name__)


@cached()
def get_related_entities(
    adapter: DatabaseAdapter,
    entity_id: str,
    relationship_types: Optional[List[str]] = None,
    direction: str = "both",
    max_results: int = 10,
    include_properties: bool = True,
    callback: Optional[ProgressCallback] = None
) -> List[RelatedEntity]:
    """Get entities related to a specific entity.

    This method retrieves entities that are directly connected to the specified entity
    in the knowledge graph. It supports filtering by relationship type and direction.

    Args:
        adapter: The database adapter to use.
        entity_id: The ID of the entity.
        relationship_types: Optional list of relationship types to filter by.
        direction: Direction of relationships to include ("outgoing", "incoming", or "both").
        max_results: Maximum number of results to return.
        include_properties: Whether to include edge properties in the results.
        callback: Optional callback for progress reporting.

    Returns:
        A list of RelatedEntity objects.

    Raises:
        QueryError: If getting related entities fails.
    """
    try:
        # Report progress
        if callback:
            callback(
                ProgressStage.INITIALIZING,
                "Initializing relationship query",
                0.0
            )

        # Validate direction
        if direction not in ["outgoing", "incoming", "both"]:
            raise ValueError(f"Invalid direction: {direction}")

        # Report progress
        if callback:
            callback(
                ProgressStage.QUERYING,
                "Querying related entities",
                0.2
            )

        # Get outgoing edges if needed
        outgoing_edges = []
        if direction in ["outgoing", "both"]:
            outgoing_edges = adapter.get_edges_by_src(entity_id)

        # Get incoming edges if needed
        incoming_edges = []
        if direction in ["incoming", "both"]:
            incoming_edges = adapter.get_edges_by_dst(entity_id)

        # Report progress
        if callback:
            callback(
                ProgressStage.PROCESSING,
                "Processing relationship results",
                0.6
            )

        # Filter by relationship type if specified
        if relationship_types:
            rel_types = [r.upper() for r in relationship_types]
            outgoing_edges = [e for e in outgoing_edges if e["rel"] in rel_types]
            incoming_edges = [e for e in incoming_edges if e["rel"] in rel_types]

        # Convert to RelatedEntity models
        related_entities = []

        # Process outgoing edges
        for edge in outgoing_edges:
            # Get the target node
            target_node = adapter.get_node_by_id(edge["dst"])
            if not target_node:
                continue

            # Create RelatedEntity
            related_entity = RelatedEntity(
                id=target_node["id"],
                type=target_node["type"],
                title=target_node.get("title"),
                relationship=edge["rel"],
                direction="outgoing",
                properties=edge.get("properties", {}) if include_properties else {}
            )
            related_entities.append(related_entity)

        # Process incoming edges
        for edge in incoming_edges:
            # Get the source node
            source_node = adapter.get_node_by_id(edge["src"])
            if not source_node:
                continue

            # Create RelatedEntity
            related_entity = RelatedEntity(
                id=source_node["id"],
                type=source_node["type"],
                title=source_node.get("title"),
                relationship=edge["rel"],
                direction="incoming",
                properties=edge.get("properties", {}) if include_properties else {}
            )
            related_entities.append(related_entity)

        # Report progress
        if callback:
            callback(
                ProgressStage.COMPLETING,
                "Relationship query complete",
                1.0
            )

        # Limit results
        return related_entities[:max_results]

    except Exception as e:
        logger.exception(f"Error in get_related_entities: {e}")
        raise QueryError(f"Failed to get related entities: {e}")


@cached()
def get_entity_details(
    adapter: DatabaseAdapter,
    entity_id: str,
    include_related: bool = True,
    callback: Optional[ProgressCallback] = None
) -> EntityDetails:
    """Get detailed information about an entity.

    This method retrieves detailed information about an entity, including its
    properties and optionally its relationships with other entities.

    Args:
        adapter: The database adapter to use.
        entity_id: The ID of the entity.
        include_related: Whether to include related entities.
        callback: Optional callback for progress reporting.

    Returns:
        An EntityDetails object.

    Raises:
        QueryError: If getting entity details fails.
    """
    try:
        # Report progress
        if callback:
            callback(
                ProgressStage.INITIALIZING,
                "Initializing entity details query",
                0.0
            )

        # Get the entity
        entity = adapter.get_node_by_id(entity_id)
        if not entity:
            raise QueryError(f"Entity not found: {entity_id}")

        # Report progress
        if callback:
            callback(
                ProgressStage.PROCESSING,
                "Processing entity details",
                0.5
            )

        # Get related entities if requested
        related_entities = []
        if include_related:
            related_entities = get_related_entities(
                adapter=adapter,
                entity_id=entity_id,
                max_results=20,
                callback=None  # Don't pass the callback to avoid nested progress reporting
            )

        # Report progress
        if callback:
            callback(
                ProgressStage.COMPLETING,
                "Entity details query complete",
                1.0
            )

        # Create EntityDetails
        return EntityDetails(
            id=entity["id"],
            type=entity["type"],
            title=entity.get("title"),
            body=entity.get("body"),
            timestamp=entity.get("timestamp"),
            properties=entity.get("extra", {}),
            related_entities=related_entities
        )

    except Exception as e:
        logger.exception(f"Error in get_entity_details: {e}")
        raise QueryError(f"Failed to get entity details: {e}")
