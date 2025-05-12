"""Core implementation of the Arc Memory SDK.

This module provides the `Arc` class, which is the main entry point for the SDK.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from arc_memory.db import get_adapter
from arc_memory.db.base import DatabaseAdapter
from arc_memory.errors import ArcError, DatabaseError
from arc_memory.schema.models import Edge, Node
from arc_memory.sql.db import ensure_arc_dir, get_db_path

from arc_memory.sdk.errors import SDKError, AdapterError, QueryError, BuildError
from arc_memory.sdk.models import (
    DecisionTrailEntry, EntityDetails, HistoryEntry, ImpactResult, QueryResult, RelatedEntity
)
from arc_memory.sdk.progress import ProgressCallback


class Arc:
    """Main entry point for the Arc Memory SDK.

    This class provides methods for interacting with the Arc Memory knowledge graph.
    It is designed to be framework-agnostic, allowing integration with various agent
    frameworks through adapters.

    Attributes:
        repo_path: Path to the Git repository.
        adapter: Database adapter instance.
    """

    def __init__(
        self,
        repo_path: Union[str, Path],
        adapter_type: Optional[str] = None,
        connection_params: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the Arc Memory SDK.

        Args:
            repo_path: Path to the Git repository.
            adapter_type: Type of database adapter to use. If None, uses the configured adapter.
            connection_params: Parameters for connecting to the database.
                If None, uses default parameters.

        Raises:
            SDKError: If initialization fails.
            AdapterError: If the adapter cannot be initialized.
        """
        try:
            self.repo_path = Path(repo_path)

            # Get the database adapter
            self.adapter = get_adapter(adapter_type)

            # Connect to the database
            if not connection_params:
                # Use default connection parameters
                db_path = get_db_path()
                connection_params = {"db_path": str(db_path)}

            # Connect to the database
            self.adapter.connect(connection_params)

            # Initialize the database schema if needed
            if not self.adapter.is_connected():
                raise AdapterError("Failed to connect to the database")

            # Initialize the database schema
            self.adapter.init_db()

        except DatabaseError as e:
            # Convert database errors to SDK errors
            raise AdapterError(f"Database adapter error: {e}", details=e.details) from e
        except Exception as e:
            # Convert other exceptions to SDK errors
            raise SDKError(f"Failed to initialize Arc Memory SDK: {e}") from e

    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by its ID.

        Args:
            node_id: The ID of the node.

        Returns:
            The node as a dictionary, or None if it doesn't exist.

        Raises:
            QueryError: If getting the node fails.
        """
        try:
            return self.adapter.get_node_by_id(node_id)
        except Exception as e:
            raise QueryError(f"Failed to get node by ID: {e}") from e

    def add_nodes_and_edges(self, nodes: List[Node], edges: List[Edge]) -> None:
        """Add nodes and edges to the knowledge graph.

        Args:
            nodes: The nodes to add.
            edges: The edges to add.

        Raises:
            BuildError: If adding nodes and edges fails.
        """
        try:
            self.adapter.add_nodes_and_edges(nodes, edges)
        except Exception as e:
            raise BuildError(f"Failed to add nodes and edges: {e}") from e

    def get_node_count(self) -> int:
        """Get the number of nodes in the knowledge graph.

        Returns:
            The number of nodes.

        Raises:
            QueryError: If getting the node count fails.
        """
        try:
            return self.adapter.get_node_count()
        except Exception as e:
            raise QueryError(f"Failed to get node count: {e}") from e

    def get_edge_count(self) -> int:
        """Get the number of edges in the knowledge graph.

        Returns:
            The number of edges.

        Raises:
            QueryError: If getting the edge count fails.
        """
        try:
            return self.adapter.get_edge_count()
        except Exception as e:
            raise QueryError(f"Failed to get edge count: {e}") from e

    def get_edges_by_src(self, src_id: str) -> List[Dict[str, Any]]:
        """Get edges by source node ID.

        Args:
            src_id: The ID of the source node.

        Returns:
            A list of edges as dictionaries.

        Raises:
            QueryError: If getting the edges fails.
        """
        try:
            return self.adapter.get_edges_by_src(src_id)
        except Exception as e:
            raise QueryError(f"Failed to get edges by source: {e}") from e

    def get_edges_by_dst(self, dst_id: str) -> List[Dict[str, Any]]:
        """Get edges by destination node ID.

        Args:
            dst_id: The ID of the destination node.

        Returns:
            A list of edges as dictionaries.

        Raises:
            QueryError: If getting the edges fails.
        """
        try:
            return self.adapter.get_edges_by_dst(dst_id)
        except Exception as e:
            raise QueryError(f"Failed to get edges by destination: {e}") from e

    def close(self) -> None:
        """Close the connection to the database.

        Raises:
            AdapterError: If closing the connection fails.
        """
        try:
            if self.adapter and self.adapter.is_connected():
                self.adapter.disconnect()
        except Exception as e:
            raise AdapterError(f"Failed to close database connection: {e}") from e

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.close()

    # Query API methods

    def query(
        self,
        question: str,
        max_results: int = 5,
        max_hops: int = 3,
        include_causal: bool = True,
        cache: bool = True,
        callback: Optional[ProgressCallback] = None
    ) -> QueryResult:
        """Query the knowledge graph using natural language.

        This method enables natural language queries about the codebase, focusing on
        causal relationships and decision trails. It's particularly useful for understanding
        why certain changes were made and their implications.

        Args:
            question: The natural language question to ask.
            max_results: Maximum number of results to return.
            max_hops: Maximum number of hops in the graph traversal.
            include_causal: Whether to prioritize causal relationships.
            cache: Whether to use cached results if available. When True (default),
                results are cached and retrieved from cache if a matching query exists.
                Set to False to force a fresh query execution.
            callback: Optional callback for progress reporting.

        Returns:
            A QueryResult containing the answer and supporting evidence.

        Raises:
            QueryError: If the query fails.
        """
        from arc_memory.sdk.query import query_knowledge_graph
        return query_knowledge_graph(
            adapter=self.adapter,
            question=question,
            max_results=max_results,
            max_hops=max_hops,
            include_causal=include_causal,
            cache=cache,
            callback=callback
        )

    # Decision Trail API methods

    def get_decision_trail(
        self,
        file_path: str,
        line_number: int,
        max_results: int = 5,
        max_hops: int = 3,
        include_rationale: bool = True,
        cache: bool = True,
        callback: Optional[ProgressCallback] = None
    ) -> List[DecisionTrailEntry]:
        """Get the decision trail for a specific line in a file.

        This method traces the history of a specific line in a file, showing the commit
        that last modified it and related entities such as PRs, issues, and ADRs. It's
        particularly useful for understanding why a particular piece of code exists.

        Args:
            file_path: Path to the file, relative to the repository root.
            line_number: Line number to trace (1-based).
            max_results: Maximum number of results to return.
            max_hops: Maximum number of hops in the graph traversal.
            include_rationale: Whether to extract decision rationales.
            cache: Whether to use cached results if available. When True (default),
                results are cached and retrieved from cache if a matching query exists.
                Set to False to force a fresh query execution.
            callback: Optional callback for progress reporting.

        Returns:
            A list of DecisionTrailEntry objects representing the decision trail.

        Raises:
            QueryError: If getting the decision trail fails.
        """
        from arc_memory.sdk.decision_trail import get_decision_trail
        return get_decision_trail(
            adapter=self.adapter,
            file_path=file_path,
            line_number=line_number,
            max_results=max_results,
            max_hops=max_hops,
            include_rationale=include_rationale,
            cache=cache,
            callback=callback
        )

    # Entity Relationship API methods

    def get_related_entities(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        direction: str = "both",
        max_results: int = 10,
        include_properties: bool = True,
        cache: bool = True,
        callback: Optional[ProgressCallback] = None
    ) -> List[RelatedEntity]:
        """Get entities related to a specific entity.

        This method retrieves entities that are directly connected to the specified entity
        in the knowledge graph. It supports filtering by relationship type and direction.

        Args:
            entity_id: The ID of the entity.
            relationship_types: Optional list of relationship types to filter by.
            direction: Direction of relationships to include ("outgoing", "incoming", or "both").
            max_results: Maximum number of results to return.
            include_properties: Whether to include edge properties in the results.
            cache: Whether to use cached results if available. When True (default),
                results are cached and retrieved from cache if a matching query exists.
                Set to False to force a fresh query execution.
            callback: Optional callback for progress reporting.

        Returns:
            A list of RelatedEntity objects.

        Raises:
            QueryError: If getting related entities fails.
        """
        from arc_memory.sdk.relationships import get_related_entities
        return get_related_entities(
            adapter=self.adapter,
            entity_id=entity_id,
            relationship_types=relationship_types,
            direction=direction,
            max_results=max_results,
            include_properties=include_properties,
            cache=cache,
            callback=callback
        )

    def get_entity_details(
        self,
        entity_id: str,
        include_related: bool = True,
        cache: bool = True,
        callback: Optional[ProgressCallback] = None
    ) -> EntityDetails:
        """Get detailed information about an entity.

        This method retrieves detailed information about an entity, including its
        properties and optionally its relationships with other entities.

        Args:
            entity_id: The ID of the entity.
            include_related: Whether to include related entities.
            cache: Whether to use cached results if available. When True (default),
                results are cached and retrieved from cache if a matching query exists.
                Set to False to force a fresh query execution.
            callback: Optional callback for progress reporting.

        Returns:
            An EntityDetails object.

        Raises:
            QueryError: If getting entity details fails.
        """
        from arc_memory.sdk.relationships import get_entity_details
        return get_entity_details(
            adapter=self.adapter,
            entity_id=entity_id,
            include_related=include_related,
            cache=cache,
            callback=callback
        )

    # Component Impact API methods

    def analyze_component_impact(
        self,
        component_id: str,
        impact_types: Optional[List[str]] = None,
        max_depth: int = 3,
        cache: bool = True,
        callback: Optional[ProgressCallback] = None
    ) -> List[ImpactResult]:
        """Analyze the potential impact of changes to a component.

        This method identifies components that may be affected by changes to the
        specified component, based on historical co-change patterns and explicit
        dependencies in the knowledge graph.

        Args:
            component_id: The ID of the component to analyze.
            impact_types: Types of impact to include (direct, indirect, potential).
            max_depth: Maximum depth of impact analysis.
            cache: Whether to use cached results if available. When True (default),
                results are cached and retrieved from cache if a matching query exists.
                Set to False to force a fresh query execution.
            callback: Optional callback for progress reporting.

        Returns:
            A list of ImpactResult objects representing affected components.

        Raises:
            QueryError: If the impact analysis fails.
        """
        from arc_memory.sdk.impact import analyze_component_impact
        return analyze_component_impact(
            adapter=self.adapter,
            component_id=component_id,
            impact_types=impact_types,
            max_depth=max_depth,
            cache=cache,
            callback=callback
        )

    # Temporal Analysis API methods

    def get_entity_history(
        self,
        entity_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_related: bool = False,
        cache: bool = True,
        callback: Optional[ProgressCallback] = None
    ) -> List[HistoryEntry]:
        """Get the history of an entity over time.

        This method retrieves the history of an entity, showing how it has changed
        over time and how it has been referenced by other entities.

        Args:
            entity_id: The ID of the entity.
            start_date: Optional start date for the history.
            end_date: Optional end date for the history.
            include_related: Whether to include related entities in the history.
            cache: Whether to use cached results if available. When True (default),
                results are cached and retrieved from cache if a matching query exists.
                Set to False to force a fresh query execution.
            callback: Optional callback for progress reporting.

        Returns:
            A list of HistoryEntry objects representing the entity's history.

        Raises:
            QueryError: If getting the entity history fails.
        """
        from arc_memory.sdk.temporal import get_entity_history
        return get_entity_history(
            adapter=self.adapter,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            include_related=include_related,
            cache=cache,
            callback=callback
        )
