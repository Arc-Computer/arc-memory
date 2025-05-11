"""Linear-specific refresh implementation for Arc Memory.

This module provides Linear-specific implementation for refreshing the knowledge graph
with the latest data from Linear.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from arc_memory.auth.linear import get_linear_token
from arc_memory.db.metadata import get_refresh_timestamp
from arc_memory.errors import AutoRefreshError, LinearAuthError
from arc_memory.ingest.linear import LinearIngestor
from arc_memory.logging_conf import get_logger
from arc_memory.sql.db import add_nodes_and_edges

logger = get_logger(__name__)


def refresh() -> bool:
    """Refresh the knowledge graph with the latest data from Linear.
    
    Returns:
        True if the refresh was successful, False otherwise.
    
    Raises:
        AutoRefreshError: If refreshing from Linear fails.
    """
    try:
        # Get the Linear token
        token = get_linear_token()
        if not token:
            error_msg = "Linear token not found. Please authenticate with 'arc auth linear'"
            logger.error(error_msg)
            raise LinearAuthError(error_msg)
        
        # Get the last refresh timestamp
        last_refresh = get_refresh_timestamp("linear")
        
        # Create a Linear ingestor
        ingestor = LinearIngestor()
        
        # Ingest data from Linear
        logger.info("Ingesting data from Linear")
        nodes, edges, last_processed = ingestor.ingest(
            last_processed={"last_refresh": last_refresh.isoformat()} if last_refresh else None
        )
        
        # Add the nodes and edges to the knowledge graph
        if nodes or edges:
            logger.info(f"Adding {len(nodes)} nodes and {len(edges)} edges to the knowledge graph")
            add_nodes_and_edges(nodes, edges)
            logger.info("Successfully added Linear data to the knowledge graph")
        else:
            logger.info("No new data to add from Linear")
        
        return True
    except Exception as e:
        error_msg = f"Failed to refresh Linear data: {e}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "source": "linear",
                "error": str(e),
            }
        )
