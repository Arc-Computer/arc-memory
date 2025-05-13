"""Arc Memory SDK - Framework-agnostic SDK for Arc Memory.

This package provides a clean, intuitive interface for interacting with Arc Memory's
knowledge graph, designed for both direct use and integration with agent frameworks.

The main entry point is the `Arc` class, which provides methods for querying and
modifying the knowledge graph.

Example:
    ```python
    from arc_memory.sdk import Arc

    # Initialize Arc with the repository path
    arc = Arc(repo_path="./")

    # Get a node by ID
    node = arc.get_node_by_id("commit:abc123")

    # Add nodes and edges to the graph
    arc.add_nodes_and_edges(nodes, edges)

    # Query the knowledge graph
    result = arc.query("Who implemented the authentication feature?")
    ```
"""

from arc_memory.sdk.core import Arc
from arc_memory.sdk.adapters import discover_adapters

# Discover and register framework adapters
discover_adapters()

__all__ = ["Arc"]
