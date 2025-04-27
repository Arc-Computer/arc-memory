"""Test database functionality for Arc Memory.

This module provides mock database functionality for testing without a real database.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from arc_memory.errors import DatabaseError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    BuildManifest,
    Edge,
    EdgeRel,
    Node,
    NodeType,
    SearchResult,
)

logger = get_logger(__name__)


class MockConnection:
    """Mock database connection for testing."""

    def __init__(self):
        """Initialize the mock connection."""
        self.nodes = {}
        self.edges = []
        self.cursor_results = []
        self.cursor_index = 0

    def execute(self, query: str, params: Tuple = None) -> "MockCursor":
        """Execute a query.

        Args:
            query: The SQL query to execute.
            params: The parameters for the query.

        Returns:
            A mock cursor.
        """
        logger.debug(f"Mock execute: {query}")
        if params:
            logger.debug(f"  with params: {params}")

        # Handle specific queries
        if "COUNT(*) FROM nodes" in query:
            self.cursor_results = [(len(self.nodes),)]
        elif "COUNT(*) FROM edges" in query:
            self.cursor_results = [(len(self.edges),)]
        elif "INSERT OR REPLACE INTO nodes" in query:
            # This is handled in add_nodes_and_edges
            pass
        elif "INSERT OR REPLACE INTO edges" in query:
            # This is handled in add_nodes_and_edges
            pass
        elif "SELECT id, type, title, body, extra FROM nodes WHERE id = ?" in query:
            node_id = params[0]
            if node_id in self.nodes:
                node = self.nodes[node_id]
                self.cursor_results = [(
                    node.id,
                    node.type.value,
                    node.title,
                    node.body,
                    json.dumps(node.extra),
                )]
            else:
                self.cursor_results = []
        else:
            # Default empty result
            self.cursor_results = []

        return MockCursor(self)

    def cursor(self) -> "MockCursor":
        """Get a cursor.

        Returns:
            A mock cursor.
        """
        return MockCursor(self)

    def close(self) -> None:
        """Close the connection."""
        pass

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass


class MockCursor:
    """Mock database cursor for testing."""

    def __init__(self, connection: MockConnection):
        """Initialize the mock cursor.

        Args:
            connection: The mock connection.
        """
        self.connection = connection
        self.row_index = 0

    def execute(self, query: str, params: Tuple = None) -> "MockCursor":
        """Execute a query.

        Args:
            query: The SQL query to execute.
            params: The parameters for the query.

        Returns:
            Self for chaining.
        """
        return self.connection.execute(query, params)

    def fetchone(self) -> Optional[Tuple]:
        """Fetch one result.

        Returns:
            A result tuple, or None if no more results.
        """
        if not self.connection.cursor_results:
            return None
        return self.connection.cursor_results[0]

    def fetchall(self) -> List[Tuple]:
        """Fetch all results.

        Returns:
            A list of result tuples.
        """
        return self.connection.cursor_results

    def __iter__(self):
        """Iterate over results."""
        self.row_index = 0
        return self

    def __next__(self):
        """Get the next result."""
        if self.row_index >= len(self.connection.cursor_results):
            raise StopIteration
        result = self.connection.cursor_results[self.row_index]
        self.row_index += 1
        return result


def get_mock_connection() -> MockConnection:
    """Get a mock database connection.

    Returns:
        A mock connection.
    """
    return MockConnection()


def init_test_db() -> MockConnection:
    """Initialize a test database.

    Returns:
        A mock connection.
    """
    logger.info("Initializing test database")
    return get_mock_connection()


def add_test_nodes_and_edges(
    conn: MockConnection, nodes: List[Node], edges: List[Edge]
) -> None:
    """Add nodes and edges to the test database.

    Args:
        conn: A mock connection.
        nodes: The nodes to add.
        edges: The edges to add.
    """
    for node in nodes:
        conn.nodes[node.id] = node

    for edge in edges:
        conn.edges.append(edge)

    logger.info(f"Added {len(nodes)} nodes and {len(edges)} edges to the test database")


def get_test_node_by_id(conn: MockConnection, node_id: str) -> Optional[Dict[str, Any]]:
    """Get a node by its ID from the test database.

    Args:
        conn: A mock connection.
        node_id: The ID of the node.

    Returns:
        The node, or None if it doesn't exist.
    """
    if node_id not in conn.nodes:
        return None

    node = conn.nodes[node_id]
    return {
        "id": node.id,
        "type": node.type.value,
        "title": node.title,
        "body": node.body,
        "extra": node.extra,
    }


def get_test_edges_by_src(
    conn: MockConnection, src_id: str, rel_type: Optional[EdgeRel] = None
) -> List[Dict[str, Any]]:
    """Get edges by source node ID from the test database.

    Args:
        conn: A mock connection.
        src_id: The ID of the source node.
        rel_type: Optional relationship type to filter by.

    Returns:
        A list of edges.
    """
    edges = []
    for edge in conn.edges:
        if edge.src == src_id and (rel_type is None or edge.rel == rel_type):
            edges.append({
                "src": edge.src,
                "dst": edge.dst,
                "rel": edge.rel.value,
                "properties": edge.properties,
            })
    return edges


def get_test_edges_by_dst(
    conn: MockConnection, dst_id: str, rel_type: Optional[EdgeRel] = None
) -> List[Dict[str, Any]]:
    """Get edges by destination node ID from the test database.

    Args:
        conn: A mock connection.
        dst_id: The ID of the destination node.
        rel_type: Optional relationship type to filter by.

    Returns:
        A list of edges.
    """
    edges = []
    for edge in conn.edges:
        if edge.dst == dst_id and (rel_type is None or edge.rel == rel_type):
            edges.append({
                "src": edge.src,
                "dst": edge.dst,
                "rel": edge.rel.value,
                "properties": edge.properties,
            })
    return edges


def get_test_node_count(conn: MockConnection) -> int:
    """Get the number of nodes in the test database.

    Args:
        conn: A mock connection.

    Returns:
        The number of nodes.
    """
    return len(conn.nodes)


def get_test_edge_count(conn: MockConnection) -> int:
    """Get the number of edges in the test database.

    Args:
        conn: A mock connection.

    Returns:
        The number of edges.
    """
    return len(conn.edges)


def search_test_entities(
    conn: MockConnection, query: str, limit: int = 5
) -> List[SearchResult]:
    """Search for entities in the test database.

    Args:
        conn: A mock connection.
        query: The search query.
        limit: The maximum number of results to return.

    Returns:
        A list of search results.
    """
    # Simple search implementation for testing
    results = []
    for node_id, node in conn.nodes.items():
        if (
            (node.title and query.lower() in node.title.lower())
            or (node.body and query.lower() in node.body.lower())
        ):
            results.append(
                SearchResult(
                    id=node.id,
                    type=node.type,
                    title=node.title or "",
                    snippet=node.body[:100] + "..." if node.body and len(node.body) > 100 else node.body or "",
                    score=1.0,
                )
            )
            if len(results) >= limit:
                break
    return results
