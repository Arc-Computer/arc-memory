"""Helper functions for benchmarking the build process."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from arc_memory.plugins import discover_plugins
from arc_memory.schema.models import BuildManifest
from arc_memory.sql.db import (
    compress_db,
    ensure_arc_dir,
    init_db,
    load_build_manifest,
    save_build_manifest,
)


def build_graph(
    repo_path: Path,
    output_path: Optional[Path] = None,
    max_commits: int = 5000,
    days: int = 365,
    incremental: bool = False,
    token: Optional[str] = None,
) -> Tuple[int, int, Dict[str, Any]]:
    """Build the knowledge graph from Git, GitHub, and ADRs.

    Args:
        repo_path: Path to the Git repository.
        output_path: Path to the output database file.
        max_commits: Maximum number of commits to process.
        days: Maximum age of commits to process in days.
        incremental: Whether to perform an incremental build.
        token: GitHub token to use for API calls.

    Returns:
        A tuple of (node_count, edge_count, plugin_metadata).
    """
    # Ensure output directory exists
    arc_dir = ensure_arc_dir()
    if output_path is None:
        output_path = arc_dir / "graph.db"

    # Check if repo_path is a Git repository
    if not (repo_path / ".git").exists():
        raise ValueError(f"Error: {repo_path} is not a Git repository.")

    # Load existing manifest for incremental builds
    manifest = None
    if incremental:
        manifest = load_build_manifest()
        if manifest is None:
            print("No existing build manifest found. Performing full build.")
            incremental = False

    # Initialize database
    conn = init_db(output_path)

    # Discover plugins
    registry = discover_plugins()

    # Initialize lists for all nodes and edges
    all_nodes = []
    all_edges = []
    plugin_metadata = {}

    # Process each plugin
    for plugin in registry.get_all():
        plugin_name = plugin.get_name()

        # Get last processed data for this plugin
        last_processed_data = None
        if manifest and incremental and plugin_name in manifest.last_processed:
            last_processed_data = manifest.last_processed[plugin_name]

        # Special handling for Git plugin (pass max_commits and days)
        if plugin_name == "git":
            nodes, edges, metadata = plugin.ingest(
                repo_path,
                max_commits=max_commits,
                days=days,
                last_processed=last_processed_data,
            )
        # Special handling for GitHub plugin (pass token)
        # Only use GitHub plugin for our own repository to avoid authentication issues
        elif plugin_name == "github" and repo_path.name == "arc-memory":
            try:
                nodes, edges, metadata = plugin.ingest(
                    repo_path,
                    token=token,
                    last_processed=last_processed_data,
                )
            except Exception as e:
                print(f"GitHub plugin failed: {e}")
                print("Continuing without GitHub data")
                nodes, edges, metadata = [], [], {}
        elif plugin_name == "github":
            print(f"Skipping GitHub plugin for external repository: {repo_path.name}")
            nodes, edges, metadata = [], [], {}
        # Default handling for other plugins
        else:
            nodes, edges, metadata = plugin.ingest(
                repo_path,
                last_processed=last_processed_data,
            )

        # Add results to the combined lists
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        plugin_metadata[plugin_name] = metadata

    # Write to database
    from arc_memory.sql.db import add_nodes_and_edges
    add_nodes_and_edges(conn, all_nodes, all_edges)

    # Get the node and edge counts
    from arc_memory.sql.db import get_node_count, get_edge_count
    node_count = get_node_count(conn)
    edge_count = get_edge_count(conn)

    # Compress database
    compressed_path = compress_db(output_path)

    # Create and save build manifest
    # Get the last commit hash from the git plugin metadata
    last_commit_hash = None
    if "git" in plugin_metadata and "last_commit_hash" in plugin_metadata["git"]:
        last_commit_hash = plugin_metadata["git"]["last_commit_hash"]

    build_manifest = BuildManifest(
        schema_version="0.1.0",
        build_time=datetime.now(),
        commit=last_commit_hash,
        node_count=node_count,
        edge_count=edge_count,
        last_processed=plugin_metadata,
    )
    save_build_manifest(build_manifest)

    return node_count, edge_count, plugin_metadata
