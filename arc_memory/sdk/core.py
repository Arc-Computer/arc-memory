"""Core implementation of the Arc Memory SDK.

This module provides the `Arc` class, which is the main entry point for the SDK.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from arc_memory.db import get_adapter
from arc_memory.db.base import DatabaseAdapter
from arc_memory.errors import ArcError, DatabaseError
from arc_memory.schema.models import Edge, Node
from arc_memory.sql.db import ensure_arc_dir, get_db_path

from arc_memory.sdk.errors import SDKError, AdapterError, QueryError, BuildError


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
