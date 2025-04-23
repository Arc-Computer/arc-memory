"""Trace history functionality for Arc Memory.

This module provides functions to trace the history of a specific line in a file,
following the decision trail through commits, PRs, issues, and ADRs.
"""

import json
import os
import sqlite3
import subprocess
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Any

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Node, NodeType
from arc_memory.sql.db import get_connection

logger = get_logger(__name__)

# Cache size for git blame results
BLAME_CACHE_SIZE = 100


@lru_cache(maxsize=BLAME_CACHE_SIZE)
def get_commit_for_line(repo_path: Path, file_path: str, line_number: int) -> Optional[str]:
    """
    Use git blame to find the commit that last modified a specific line.

    Args:
        repo_path: Path to the Git repository
        file_path: Path to the file, relative to the repository root
        line_number: Line number to check (1-based)

    Returns:
        The commit hash, or None if not found
    """
    try:
        # Ensure the file path is relative to the repository root
        if os.path.isabs(file_path):
            try:
                file_path = os.path.relpath(file_path, repo_path)
            except ValueError:
                logger.error(f"File {file_path} is not within repository {repo_path}")
                return None

        # Run git blame to get the commit hash for the specified line
        cmd = [
            "git", "-C", str(repo_path), "blame",
            "-L", f"{line_number},{line_number}",
            "--porcelain",
            file_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the output to extract the commit hash
        # The first line of git blame --porcelain output starts with the commit hash
        lines = result.stdout.strip().split('\n')
        if not lines:
            logger.warning(f"No blame information for {file_path}:{line_number}")
            return None

        # Extract the commit hash from the first line
        # Format: <hash> <original line> <line number> <line count>
        commit_hash = lines[0].split(' ')[0]

        logger.debug(f"Found commit {commit_hash} for {file_path}:{line_number}")
        return commit_hash

    except subprocess.CalledProcessError as e:
        logger.error(f"Git blame failed: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Error in get_commit_for_line: {e}")
        return None


def trace_history(
    conn: sqlite3.Connection, file_path: str, line_number: int, max_nodes: int = 3
) -> List[Dict[str, Any]]:
    """
    Trace the history of a file line.

    Args:
        conn: SQLite connection
        file_path: Path to the file, relative to the repository root
        line_number: Line number to check (1-based)
        max_nodes: Maximum number of nodes to return

    Returns:
        A list of nodes representing the history trail
    """
    try:
        # This is a placeholder implementation
        # In a real implementation, we would:
        # 1. Get the commit for the line using git blame
        # 2. Trace the history of the commit
        # 3. Format the results

        # Get the current working directory
        cwd = os.getcwd()
        repo_path = Path(cwd)

        # Get the commit for the line
        commit_id = get_commit_for_line(repo_path, file_path, line_number)
        if not commit_id:
            logger.warning(f"No commit found for {file_path}:{line_number}")
            return []

        # Start with the commit node
        start_node_id = f"commit:{commit_id}"

        # Get the commit node
        commit_node = get_node_by_id(conn, start_node_id)
        if not commit_node:
            logger.warning(f"Commit node not found: {start_node_id}")
            return []

        # Format the result
        result = [{
            "type": "commit",
            "id": start_node_id,
            "title": commit_node.title or "",
            "timestamp": commit_node.ts.isoformat() if commit_node.ts else None
        }]

        # Return the result (limited to max_nodes)
        return result[:max_nodes]

    except Exception as e:
        logger.error(f"Error in trace_history: {e}")
        return []


def get_node_by_id(conn: sqlite3.Connection, node_id: str) -> Optional[Node]:
    """
    Get a node from the database by its ID.

    Args:
        conn: SQLite connection
        node_id: The node ID to retrieve

    Returns:
        The node, or None if not found
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, type, title, body, extra FROM nodes WHERE id = ?",
            (node_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        id_val, type_val, title, body, extra_json = row

        # Parse the node type
        node_type = NodeType(type_val) if type_val in [e.value for e in NodeType] else None

        # Parse the extra JSON
        try:
            extra = json.loads(extra_json) if extra_json else {}
        except json.JSONDecodeError:
            extra = {}

        # Create and return the node
        return Node(
            id=id_val,
            type=node_type,
            title=title,
            body=body,
            extra=extra
        )

    except Exception as e:
        logger.error(f"Error in get_node_by_id: {e}")
        return None


def get_connected_nodes(conn: sqlite3.Connection, node_id: str, hop_count: int) -> List[str]:
    """
    Get nodes connected to the given node based on the hop count and node type.

    Args:
        conn: SQLite connection
        node_id: The node ID to start from
        hop_count: Current hop count in the BFS

    Returns:
        List of connected node IDs
    """
    try:
        # Extract node type from the ID
        node_type = node_id.split(':')[0] if ':' in node_id else None

        # Define the edge relationships to follow based on the node type and hop count
        if node_type == "commit" and hop_count == 0:
            # Commit → PR via MERGES
            return get_nodes_by_edge(conn, node_id, "MERGES", is_source=True)

        elif node_type == "pr" and hop_count == 1:
            # PR → Issue via MENTIONS
            return get_nodes_by_edge(conn, node_id, "MENTIONS", is_source=True)

        elif node_type == "issue" and hop_count == 1:
            # Issue → ADR via DECIDES (inbound)
            return get_nodes_by_edge(conn, node_id, "DECIDES", is_source=False)

        return []

    except Exception as e:
        logger.error(f"Error in get_connected_nodes: {e}")
        return []


def get_nodes_by_edge(conn: sqlite3.Connection, node_id: str, rel_type: str, is_source: bool) -> List[str]:
    """
    Get nodes connected by a specific edge type.

    Args:
        conn: SQLite connection
        node_id: The node ID to start from
        rel_type: The relationship type to follow
        is_source: If True, node_id is the source; otherwise, it's the destination

    Returns:
        List of connected node IDs
    """
    try:
        cursor = conn.cursor()

        if is_source:
            # node_id is the source, get destinations
            cursor.execute(
                "SELECT dst FROM edges WHERE src = ? AND rel = ?",
                (node_id, rel_type)
            )
        else:
            # node_id is the destination, get sources
            cursor.execute(
                "SELECT src FROM edges WHERE dst = ? AND rel = ?",
                (node_id, rel_type)
            )

        return [row[0] for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"Error in get_nodes_by_edge: {e}")
        return []


def format_trace_results(nodes: List[Node]) -> List[Dict[str, Any]]:
    """
    Format the trace results according to the API specification.

    Args:
        nodes: List of nodes from the trace_history function

    Returns:
        Formatted results as specified in the API docs
    """
    try:
        # Sort by timestamp (newest first)
        sorted_nodes = sorted(
            nodes,
            key=lambda n: n.ts or datetime.min,
            reverse=True
        )

        # Format according to API spec
        return [
            {
                "type": node.type,
                "id": node.id,
                "title": node.title or "",
                "timestamp": node.ts.isoformat() if node.ts else None
            }
            for node in sorted_nodes
        ]

    except Exception as e:
        logger.error(f"Error in format_trace_results: {e}")
        return []


def trace_history_for_file_line(
    db_path: Path,
    file_path: str,
    line_number: int,
    max_results: int = 3
) -> List[Dict[str, Any]]:
    """
    Trace the history of a specific line in a file.

    Args:
        db_path: Path to the SQLite database
        file_path: Path to the file, relative to the repository root
        line_number: Line number to check (1-based)
        max_results: Maximum number of results to return

    Returns:
        Formatted results as specified in the API docs
    """
    try:
        # Get a connection to the database
        conn = get_connection(db_path)

        # Call the trace_history function
        results = trace_history(conn, file_path, line_number, max_nodes=max_results)

        # Close the connection
        conn.close()

        return results

    except Exception as e:
        logger.error(f"Error in trace_history_for_file_line: {e}")
        return []
