"""GitHub-specific refresh implementation for Arc Memory.

This module provides GitHub-specific implementation for refreshing the knowledge graph
with the latest data from GitHub.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from arc_memory.auth.github import get_github_token
from arc_memory.db.metadata import get_refresh_timestamp
from arc_memory.errors import AutoRefreshError, GitHubAuthError
from arc_memory.ingest.github import GitHubIngestor
from arc_memory.logging_conf import get_logger
from arc_memory.sql.db import add_nodes_and_edges

logger = get_logger(__name__)


def refresh() -> bool:
    """Refresh the knowledge graph with the latest data from GitHub.
    
    Returns:
        True if the refresh was successful, False otherwise.
    
    Raises:
        AutoRefreshError: If refreshing from GitHub fails.
    """
    try:
        # Get the GitHub token
        token = get_github_token()
        if not token:
            error_msg = "GitHub token not found. Please authenticate with 'arc auth gh'"
            logger.error(error_msg)
            raise GitHubAuthError(error_msg)
        
        # Get the last refresh timestamp
        last_refresh = get_refresh_timestamp("github")
        
        # Create a GitHub ingestor
        ingestor = GitHubIngestor()
        
        # Ingest data from GitHub
        logger.info("Ingesting data from GitHub")
        nodes, edges, last_processed = ingestor.ingest(
            last_processed={"last_refresh": last_refresh.isoformat()} if last_refresh else None
        )
        
        # Add the nodes and edges to the knowledge graph
        if nodes or edges:
            logger.info(f"Adding {len(nodes)} nodes and {len(edges)} edges to the knowledge graph")
            add_nodes_and_edges(nodes, edges)
            logger.info("Successfully added GitHub data to the knowledge graph")
        else:
            logger.info("No new data to add from GitHub")
        
        return True
    except Exception as e:
        error_msg = f"Failed to refresh GitHub data: {e}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "source": "github",
                "error": str(e),
            }
        )
