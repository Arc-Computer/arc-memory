"""Trace history functionality for Arc Memory.

This module provides functions to trace the history of a specific line in a file,
following the decision trail through commits, PRs, issues, and ADRs.
"""

import os
import sqlite3
import subprocess
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Node, Edge, NodeType
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


def trace_history(db_path: Path, commit_id: str, max_hops: int = 2, max_results: int = 3) -> List[Node]:
    """
    Trace the history of a commit using a BFS algorithm.
    
    Args:
        db_path: Path to the SQLite database
        commit_id: The commit hash to start from
        max_hops: Maximum number of hops in the graph
        max_results: Maximum number of results to return
        
    Returns:
        A list of nodes representing the history trail
    """
    try:
        # Connect to the database
        conn = get_connection(db_path)
        
        # Start with the commit node
        start_node_id = f"commit:{commit_id}"
        
        # Initialize BFS
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(start_node_id, 0)]  # (node_id, hop_count)
        result_nodes: List[Node] = []
        
        # Perform BFS
        while queue and len(result_nodes) < max_results:
            node_id, hop_count = queue.pop(0)
            
            # Skip if already visited or max hops reached
            if node_id in visited or hop_count > max_hops:
                continue
            
            visited.add(node_id)
            
            # Get the node from the database
            node = get_node_by_id(conn, node_id)
            if node:
                result_nodes.append(node)
            
            # If we've reached max hops, don't explore further
            if hop_count >= max_hops:
                continue
            
            # Get connected nodes based on the current node type
            connected_nodes = get_connected_nodes(conn, node_id, hop_count)
            
            # Add connected nodes to the queue
            for connected_id in connected_nodes:
                if connected_id not in visited:
                    queue.append((connected_id, hop_count + 1))
        
        return result_nodes
    
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
        
        # Create and return the node
        return Node(
            id=id_val,
            type=node_type,
            title=title,
            body=body,
            extra=extra_json
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
    repo_path: Path,
    db_path: Path,
    file_path: str,
    line_number: int,
    max_results: int = 3
) -> List[Dict[str, Any]]:
    """
    Trace the history of a specific line in a file.
    
    Args:
        repo_path: Path to the Git repository
        db_path: Path to the SQLite database
        file_path: Path to the file, relative to the repository root
        line_number: Line number to check (1-based)
        max_results: Maximum number of results to return
        
    Returns:
        Formatted results as specified in the API docs
    """
    try:
        # Get the commit for the line
        commit_id = get_commit_for_line(repo_path, file_path, line_number)
        if not commit_id:
            logger.warning(f"No commit found for {file_path}:{line_number}")
            return []
        
        # Trace the history
        nodes = trace_history(db_path, commit_id, max_hops=2, max_results=max_results)
        
        # Format the results
        return format_trace_results(nodes)
    
    except Exception as e:
        logger.error(f"Error in trace_history_for_file_line: {e}")
        return []
