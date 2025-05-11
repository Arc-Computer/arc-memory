"""ADR-specific refresh implementation for Arc Memory.

This module provides ADR-specific implementation for refreshing the knowledge graph
with the latest data from Architectural Decision Records (ADRs).
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from arc_memory.db.metadata import get_refresh_timestamp
from arc_memory.errors import AutoRefreshError
from arc_memory.ingest.adr import ADRIngestor
from arc_memory.logging_conf import get_logger


logger = get_logger(__name__)


def refresh(adapter=None) -> bool:
    """Refresh the knowledge graph with the latest data from ADRs.

    Args:
        adapter: The database adapter to use. If None, a new adapter will be created.

    Returns:
        True if the refresh was successful, False otherwise.

    Raises:
        AutoRefreshError: If refreshing from ADRs fails.
    """
    try:
        # Get the current working directory
        cwd = Path.cwd()

        # Get the last refresh timestamp
        last_refresh = get_refresh_timestamp("adr")

        # Create an ADR ingestor
        ingestor = ADRIngestor()

        # Ingest data from ADRs
        logger.info("Ingesting data from ADRs")
        nodes, edges, last_processed = ingestor.ingest(
            last_processed={"last_refresh": last_refresh.isoformat()} if last_refresh else None
        )

        # Add the nodes and edges to the knowledge graph
        if nodes or edges:
            logger.info(f"Adding {len(nodes)} nodes and {len(edges)} edges to the knowledge graph")

            # Use the provided adapter or get a new one
            if adapter is None:
                from arc_memory.db import get_adapter
                from arc_memory.sql.db import get_db_path

                adapter = get_adapter()
                if not adapter.is_connected():
                    db_path = get_db_path()
                    adapter.connect({"db_path": str(db_path)})
                    adapter.init_db()

            # Add nodes and edges directly using the adapter
            adapter.add_nodes_and_edges(nodes, edges)

            logger.info("Successfully added ADR data to the knowledge graph")
        else:
            logger.info("No new data to add from ADRs")

        return True
    except Exception as e:
        error_msg = f"Failed to refresh ADR data: {e}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "source": "adr",
                "error": str(e),
            }
        )
