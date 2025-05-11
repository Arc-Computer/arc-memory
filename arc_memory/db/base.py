"""Database abstraction layer for Arc Memory.

This module provides abstract base classes and interfaces for database operations,
allowing Arc Memory to work with different database backends (SQLite, Neo4j).
"""

import abc
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import BuildManifest, Edge, Node, EdgeRel, NodeType

logger = get_logger(__name__)


class DatabaseAdapter(Protocol):
    """Protocol defining the interface for database adapters.

    This protocol ensures that all database adapters implement the required methods
    for interacting with the knowledge graph database, regardless of the underlying
    database technology (SQLite, Neo4j, etc.).
    """

    def get_name(self) -> str:
        """Get the name of the database adapter.

        Returns:
            The name of the database adapter.
        """
        ...

    def get_supported_versions(self) -> List[str]:
        """Get the supported versions of the database.

        Returns:
            A list of supported database versions.
        """
        ...

    def connect(self, connection_params: Dict[str, Any]) -> None:
        """Connect to the database.

        Args:
            connection_params: Parameters for connecting to the database.

        Raises:
            DatabaseError: If connecting to the database fails.
        """
        ...

    def disconnect(self) -> None:
        """Disconnect from the database.

        Raises:
            DatabaseError: If disconnecting from the database fails.
        """
        ...

    def is_connected(self) -> bool:
        """Check if the adapter is connected to the database.

        Returns:
            True if connected, False otherwise.
        """
        ...

    def init_db(self, params: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the database schema.

        Args:
            params: Optional parameters for database initialization.

        Raises:
            DatabaseInitializationError: If initializing the database fails.
        """
        ...

    def add_nodes_and_edges(self, nodes: List[Node], edges: List[Edge]) -> None:
        """Add nodes and edges to the database.

        Args:
            nodes: The nodes to add.
            edges: The edges to add.

        Raises:
            GraphBuildError: If adding nodes and edges fails.
        """
        ...

    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by its ID.

        Args:
            node_id: The ID of the node.

        Returns:
            The node as a dictionary, or None if it doesn't exist.

        Raises:
            GraphQueryError: If getting the node fails.
        """
        ...

    def get_node_count(self) -> int:
        """Get the number of nodes in the database.

        Returns:
            The number of nodes.

        Raises:
            GraphQueryError: If getting the node count fails.
        """
        ...

    def get_edge_count(self) -> int:
        """Get the number of edges in the database.

        Returns:
            The number of edges.

        Raises:
            GraphQueryError: If getting the edge count fails.
        """
        ...

    def get_edges_by_src(self, src_id: str, rel_type: Optional[EdgeRel] = None) -> List[Dict[str, Any]]:
        """Get edges by source node ID.

        Args:
            src_id: The ID of the source node.
            rel_type: Optional relationship type to filter by.

        Returns:
            A list of edges as dictionaries.

        Raises:
            GraphQueryError: If getting the edges fails.
        """
        ...

    def get_edges_by_dst(self, dst_id: str, rel_type: Optional[EdgeRel] = None) -> List[Dict[str, Any]]:
        """Get edges by destination node ID.

        Args:
            dst_id: The ID of the destination node.
            rel_type: Optional relationship type to filter by.

        Returns:
            A list of edges as dictionaries.

        Raises:
            GraphQueryError: If getting the edges fails.
        """
        ...

    def search_entities(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for entities in the database.

        Args:
            query: The search query.
            limit: The maximum number of results to return.

        Returns:
            A list of search results.

        Raises:
            GraphQueryError: If searching entities fails.
        """
        ...

    def begin_transaction(self) -> Any:
        """Begin a transaction.

        Returns:
            A transaction object.

        Raises:
            DatabaseError: If beginning the transaction fails.
        """
        ...

    def commit_transaction(self, transaction: Any) -> None:
        """Commit a transaction.

        Args:
            transaction: The transaction to commit.

        Raises:
            DatabaseError: If committing the transaction fails.
        """
        ...

    def rollback_transaction(self, transaction: Any) -> None:
        """Rollback a transaction.

        Args:
            transaction: The transaction to rollback.

        Raises:
            DatabaseError: If rolling back the transaction fails.
        """
        ...

    def save_metadata(self, key: str, value: Any) -> None:
        """Save metadata to the database.

        Args:
            key: The metadata key.
            value: The metadata value.

        Raises:
            DatabaseError: If saving the metadata fails.
        """
        ...

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the database.

        Args:
            key: The metadata key.
            default: The default value to return if the key doesn't exist.

        Returns:
            The metadata value, or the default if not found.

        Raises:
            DatabaseError: If getting the metadata fails.
        """
        ...

    def get_all_metadata(self) -> Dict[str, Any]:
        """Get all metadata from the database.

        Returns:
            A dictionary of all metadata.

        Raises:
            DatabaseError: If getting the metadata fails.
        """
        ...

    def save_refresh_timestamp(self, source: str, timestamp: datetime) -> None:
        """Save the last refresh timestamp for a source.

        Args:
            source: The source name (e.g., 'github', 'linear').
            timestamp: The timestamp of the last refresh.

        Raises:
            DatabaseError: If saving the timestamp fails.
        """
        ...

    def get_refresh_timestamp(self, source: str) -> Optional[datetime]:
        """Get the last refresh timestamp for a source.

        Args:
            source: The source name (e.g., 'github', 'linear').

        Returns:
            The timestamp of the last refresh, or None if not found.

        Raises:
            DatabaseError: If getting the timestamp fails.
        """
        ...

    def get_all_refresh_timestamps(self) -> Dict[str, datetime]:
        """Get all refresh timestamps.

        Returns:
            A dictionary mapping source names to refresh timestamps.

        Raises:
            DatabaseError: If getting the timestamps fails.
        """
        ...
