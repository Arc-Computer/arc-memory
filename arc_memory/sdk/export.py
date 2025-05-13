"""Export API for Arc Memory SDK.

This module provides methods for exporting the knowledge graph to various formats,
with support for filtering, compression, and signing.
"""

import gzip
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from arc_memory.db.base import DatabaseAdapter
from arc_memory.errors import ExportError, GitError
from arc_memory.export import (
    DateTimeEncoder,
    extract_causal_relationships,
    format_export_data,
    get_pr_modified_files,
    get_related_nodes,
    optimize_export_for_llm,
    sign_file,
)
from arc_memory.logging_conf import get_logger
from arc_memory.sdk.cache import cached
from arc_memory.sdk.errors import ExportSDKError
from arc_memory.sdk.models import ExportResult
from arc_memory.sdk.progress import ProgressCallback, ProgressStage
from arc_memory.sql.db import ensure_connection

logger = get_logger(__name__)


@cached()
def export_knowledge_graph(
    adapter: DatabaseAdapter,
    repo_path: Path,
    output_path: Union[str, Path],
    pr_sha: Optional[str] = None,
    entity_types: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    format: str = "json",
    compress: bool = False,
    sign: bool = False,
    key_id: Optional[str] = None,
    base_branch: str = "main",
    max_hops: int = 3,
    optimize_for_llm: bool = False,
    include_causal: bool = True,
    callback: Optional[ProgressCallback] = None,
) -> ExportResult:
    """Export the knowledge graph to a file.

    This method exports a subset of the knowledge graph based on the provided filters.
    It supports exporting in various formats, with options for compression and signing.

    Args:
        adapter: The database adapter to use.
        repo_path: Path to the Git repository.
        output_path: Path to save the export file.
        pr_sha: Optional SHA of a PR head commit to filter by.
        entity_types: Optional list of entity types to include.
        start_date: Optional start date for filtering entities.
        end_date: Optional end date for filtering entities.
        format: Export format (currently only "json" is supported).
        compress: Whether to compress the output file.
        sign: Whether to sign the output file with GPG.
        key_id: GPG key ID to use for signing.
        base_branch: Base branch to compare against when using pr_sha.
        max_hops: Maximum number of hops to traverse in the graph.
        optimize_for_llm: Whether to optimize the export for LLM consumption.
        include_causal: Whether to include causal relationships in the export.
        callback: Optional callback for progress reporting.

    Returns:
        An ExportResult containing information about the export.

    Raises:
        ExportSDKError: If the export fails.
    """
    try:
        start_time = datetime.now()

        # Report progress
        if callback:
            callback(
                ProgressStage.INITIALIZING,
                "Initializing export process",
                0.0
            )

        # Convert output_path to Path
        output_path = Path(output_path)

        # Get the database connection
        if not hasattr(adapter, "conn") or not adapter.conn:
            raise ExportSDKError("Database connection not available")

        conn = adapter.conn

        # Report progress
        if callback:
            callback(
                ProgressStage.PROCESSING,
                "Collecting nodes and edges to export",
                0.1
            )

        # Initialize variables for nodes and edges
        nodes = []
        edges = []
        modified_files = []

        # If PR SHA is provided, get modified files and related nodes
        if pr_sha:
            try:
                # Get modified files
                if callback:
                    callback(
                        ProgressStage.PROCESSING,
                        f"Getting files modified in PR {pr_sha}",
                        0.2
                    )

                modified_files = get_pr_modified_files(repo_path, pr_sha, base_branch)
                logger.info(f"Found {len(modified_files)} modified files")

                # Get file nodes for the modified files
                file_nodes = []
                for file_path in modified_files:
                    file_id = f"file:{file_path}"
                    node = adapter.get_node_by_id(file_id)
                    if node:
                        file_nodes.append(node["id"])

                # Get related nodes and edges
                if callback:
                    callback(
                        ProgressStage.PROCESSING,
                        f"Getting related nodes and edges (max_hops={max_hops})",
                        0.3
                    )

                nodes, edges = get_related_nodes(
                    conn,
                    file_nodes,
                    max_hops=max_hops,
                    include_adrs=True,
                    include_causal=include_causal
                )
            except GitError as e:
                raise ExportSDKError(f"Git error: {e}")

        # Filter by entity types if provided
        if entity_types and nodes:
            nodes = [n for n in nodes if n.get("type") in entity_types]

            # Filter edges to only include those connecting the filtered nodes
            node_ids = {n["id"] for n in nodes}
            edges = [e for e in edges if e["src"] in node_ids and e["dst"] in node_ids]

        # Filter by date if provided
        if (start_date or end_date) and nodes:
            filtered_nodes = []
            for node in nodes:
                # Check if the node has a timestamp
                timestamp = None
                if "extra" in node and "timestamp" in node["extra"]:
                    timestamp_str = node["extra"]["timestamp"]
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except (ValueError, TypeError):
                        pass

                # Apply date filters
                if timestamp:
                    if start_date and timestamp < start_date:
                        continue
                    if end_date and timestamp > end_date:
                        continue

                filtered_nodes.append(node)

            # Update nodes list
            nodes = filtered_nodes

            # Filter edges to only include those connecting the filtered nodes
            node_ids = {n["id"] for n in nodes}
            edges = [e for e in edges if e["src"] in node_ids and e["dst"] in node_ids]

        # Report progress
        if callback:
            callback(
                ProgressStage.PROCESSING,
                f"Formatting export data with {len(nodes)} nodes and {len(edges)} edges",
                0.6
            )

        # Format the export data
        export_data = format_export_data(
            pr_sha=pr_sha or "export",
            nodes=nodes,
            edges=edges,
            changed_files=modified_files
        )

        # Optimize the export data for LLM reasoning if enabled
        if optimize_for_llm:
            if callback:
                callback(
                    ProgressStage.PROCESSING,
                    "Optimizing export data for LLM reasoning",
                    0.7
                )
            export_data = optimize_export_for_llm(export_data)

        # Report progress
        if callback:
            callback(
                ProgressStage.FINALIZING,
                "Writing export data to file",
                0.8
            )

        # Write the export data to file
        final_path = output_path
        if compress:
            # If compress is True, ensure the output path has .gz extension
            if not str(output_path).endswith(".gz"):
                final_path = Path(f"{output_path}.gz")

            logger.info(f"Writing compressed export to {final_path}")
            with gzip.open(final_path, "wt") as f:
                json.dump(export_data, f, cls=DateTimeEncoder, indent=2)
        else:
            logger.info(f"Writing export to {output_path}")
            with open(output_path, "w") as f:
                json.dump(export_data, f, cls=DateTimeEncoder, indent=2)

        # Sign the file if requested
        signature_path = None
        if sign:
            if callback:
                callback(
                    ProgressStage.FINALIZING,
                    "Signing the export file",
                    0.9
                )

            sig_path = sign_file(final_path, key_id)
            if sig_path:
                signature_path = str(sig_path)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        # Report progress
        if callback:
            callback(
                ProgressStage.COMPLETED,
                "Export completed successfully",
                1.0
            )

        # Return the result
        return ExportResult(
            output_path=str(final_path),
            format=format,
            entity_count=len(nodes),
            relationship_count=len(edges),
            compressed=compress,
            signed=sign,
            signature_path=signature_path,
            execution_time=execution_time
        )

    except ExportSDKError:
        # Re-raise export SDK errors
        raise
    except Exception as e:
        # Convert other exceptions to export SDK errors
        raise ExportSDKError(f"Error exporting knowledge graph: {e}")
