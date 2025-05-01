"""Memory integration for Arc Memory.

This package provides functionality for storing and retrieving simulation results
in the knowledge graph, creating a reinforcing flywheel where simulation results
feed back into the knowledge graph, making future simulations more accurate and
providing richer context for decision-making.
"""

from arc_memory.memory.storage import (
    create_simulation_node,
    create_metric_nodes,
    create_simulation_edges,
    store_simulation_results,
)

from arc_memory.memory.query import (
    get_simulation_by_id,
    get_simulations_by_service,
    get_simulations_by_file,
    get_similar_simulations,
    get_simulation_metrics,
)

from arc_memory.memory.integration import (
    store_simulation_in_memory,
    retrieve_relevant_simulations,
    enhance_explanation_with_memory,
)

__all__ = [
    # Storage functions
    "create_simulation_node",
    "create_metric_nodes",
    "create_simulation_edges",
    "store_simulation_results",
    
    # Query functions
    "get_simulation_by_id",
    "get_simulations_by_service",
    "get_simulations_by_file",
    "get_similar_simulations",
    "get_simulation_metrics",
    
    # Integration functions
    "store_simulation_in_memory",
    "retrieve_relevant_simulations",
    "enhance_explanation_with_memory",
]
