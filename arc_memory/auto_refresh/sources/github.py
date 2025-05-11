"""GitHub-specific refresh implementation for Arc Memory.

This module provides GitHub-specific implementation for refreshing the knowledge graph
with the latest data from GitHub.
"""



from arc_memory.auth.github import get_github_token
from arc_memory.db.metadata import get_refresh_timestamp
from arc_memory.errors import AutoRefreshError, GitHubAuthError
from arc_memory.ingest.github import GitHubIngestor
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def refresh(adapter=None) -> bool:
    """Refresh the knowledge graph with the latest data from GitHub.

    Args:
        adapter: The database adapter to use. If None, a new adapter will be created.

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

        # Get the last refresh timestamp using the provided adapter
        if adapter:
            last_refresh = adapter.get_refresh_timestamp("github")
        else:
            last_refresh = get_refresh_timestamp("github")

        # Get the current repository path
        import os
        from pathlib import Path

        # Try to get the repository path from the environment
        repo_path = os.environ.get("ARC_REPO_PATH")
        if repo_path:
            repo_path = Path(repo_path)
        else:
            # Fall back to the current working directory
            repo_path = Path.cwd()
            logger.info(f"Using current directory as repository path: {repo_path}")

        # Create a GitHub ingestor
        ingestor = GitHubIngestor()

        # Ingest data from GitHub
        logger.info(f"Ingesting data from GitHub repository at {repo_path}")
        nodes, edges, _ = ingestor.ingest(
            repo_path=repo_path,
            token=token,
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
