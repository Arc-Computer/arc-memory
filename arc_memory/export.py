"""Export functionality for Arc Memory.

This module provides functions for exporting a relevant slice of the knowledge graph
as a JSON file for use in GitHub App PR review workflows.
"""

import gzip
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import git
from git import Repo

from arc_memory.errors import ExportError, GitError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType
from arc_memory.sql.db import (
    ensure_connection,
    get_edges_by_dst,
    get_edges_by_src,
    get_node_by_id,
)

logger = get_logger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def get_pr_modified_files(
    repo_path: Path, pr_sha: str, base_branch: str = "main"
) -> List[str]:
    """Get the list of files modified in a PR.

    Args:
        repo_path: Path to the Git repository
        pr_sha: SHA of the PR head commit
        base_branch: Base branch to compare against (default: main)

    Returns:
        List of file paths modified in the PR

    Raises:
        GitError: If there's an error accessing the Git repository
    """
    try:
        repo = Repo(repo_path)
        
        # Ensure we have the commit
        try:
            pr_commit = repo.commit(pr_sha)
        except git.exc.BadName:
            raise GitError(f"Commit {pr_sha} not found in repository")
        
        # Get the merge base between the PR commit and the base branch
        try:
            base_commit = repo.commit(base_branch)
            merge_base = repo.merge_base(base_commit, pr_commit)[0]
        except (git.exc.BadName, IndexError):
            logger.warning(f"Could not find merge base with {base_branch}, using direct diff")
            # Fall back to comparing with the parent commit
            if pr_commit.parents:
                merge_base = pr_commit.parents[0]
            else:
                raise GitError(f"Commit {pr_sha} has no parent commits")
        
        # Get the diff between the merge base and the PR head
        diff_index = merge_base.diff(pr_commit)
        
        # Extract modified file paths
        modified_files = []
        for diff in diff_index:
            if diff.a_path:
                modified_files.append(diff.a_path)
            if diff.b_path and diff.b_path != diff.a_path:
                modified_files.append(diff.b_path)
        
        return modified_files
    
    except git.exc.InvalidGitRepositoryError:
        raise GitError(f"{repo_path} is not a valid Git repository")
    except Exception as e:
        raise GitError(f"Error getting modified files: {e}")


def get_related_nodes(
    conn: Any, node_ids: List[str], max_hops: int = 1, include_adrs: bool = True
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Get nodes related to the specified nodes up to max_hops away.

    Args:
        conn: Database connection
        node_ids: List of node IDs to start from
        max_hops: Maximum number of hops to traverse
        include_adrs: Whether to include all ADRs regardless of hop distance

    Returns:
        Tuple of (nodes, edges) where each is a list of dictionaries
    """
    visited_nodes: Set[str] = set()
    visited_edges: Set[Tuple[str, str, str]] = set()
    nodes_to_visit = set(node_ids)
    
    nodes_result = []
    edges_result = []
    
    # If include_adrs is True, get all ADR nodes
    if include_adrs:
        try:
            cursor = conn.execute(
                "SELECT id, type, title, body, extra FROM nodes WHERE type = ?",
                (NodeType.ADR.value,)
            )
            for row in cursor:
                node_id = row[0]
                if node_id not in visited_nodes:
                    visited_nodes.add(node_id)
                    nodes_result.append({
                        "id": node_id,
                        "type": row[1],
                        "title": row[2],
                        "body": row[3],
                        "extra": json.loads(row[4]) if row[4] else {}
                    })
        except Exception as e:
            logger.warning(f"Error fetching ADR nodes: {e}")
    
    # BFS to get related nodes up to max_hops away
    for _ in range(max_hops):
        if not nodes_to_visit:
            break
        
        current_nodes = nodes_to_visit
        nodes_to_visit = set()
        
        for node_id in current_nodes:
            # Skip if we've already visited this node
            if node_id in visited_nodes:
                continue
            
            # Get the node
            node = get_node_by_id(conn, node_id)
            if node:
                visited_nodes.add(node_id)
                nodes_result.append(node)
            
            # Get outgoing edges
            outgoing_edges = get_edges_by_src(conn, node_id)
            for edge in outgoing_edges:
                edge_key = (edge["src"], edge["dst"], edge["rel"])
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    edges_result.append(edge)
                    nodes_to_visit.add(edge["dst"])
            
            # Get incoming edges
            incoming_edges = get_edges_by_dst(conn, node_id)
            for edge in incoming_edges:
                edge_key = (edge["src"], edge["dst"], edge["rel"])
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    edges_result.append(edge)
                    nodes_to_visit.add(edge["src"])
    
    return nodes_result, edges_result


def format_export_data(
    pr_sha: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    changed_files: List[str],
    pr_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Format the export data according to the specified schema.

    Args:
        pr_sha: SHA of the PR head commit
        nodes: List of nodes to include
        edges: List of edges to include
        changed_files: List of files changed in the PR
        pr_info: Optional PR information (number, title, author)

    Returns:
        Formatted export data as a dictionary
    """
    # Format nodes
    formatted_nodes = []
    for node in nodes:
        formatted_node = {
            "id": node["id"],
            "type": node["type"],
            "metadata": {}
        }
        
        # Add type-specific fields
        if node["type"] == NodeType.FILE.value:
            formatted_node["path"] = node["extra"].get("path", "")
            if "language" in node["extra"]:
                formatted_node["metadata"]["language"] = node["extra"]["language"]
        elif node["type"] == NodeType.COMMIT.value:
            formatted_node["title"] = node["title"]
            formatted_node["metadata"]["author"] = node["extra"].get("author", "")
            formatted_node["metadata"]["sha"] = node["extra"].get("sha", "")
        elif node["type"] == NodeType.PR.value:
            formatted_node["title"] = node["title"]
            formatted_node["metadata"]["number"] = node["extra"].get("number", 0)
            formatted_node["metadata"]["state"] = node["extra"].get("state", "")
            formatted_node["metadata"]["url"] = node["extra"].get("url", "")
        elif node["type"] == NodeType.ISSUE.value:
            formatted_node["title"] = node["title"]
            formatted_node["metadata"]["number"] = node["extra"].get("number", 0)
            formatted_node["metadata"]["state"] = node["extra"].get("state", "")
            formatted_node["metadata"]["url"] = node["extra"].get("url", "")
        elif node["type"] == NodeType.ADR.value:
            formatted_node["title"] = node["title"]
            formatted_node["path"] = node["extra"].get("path", "")
            formatted_node["metadata"]["status"] = node["extra"].get("status", "")
            formatted_node["metadata"]["decision_makers"] = node["extra"].get("decision_makers", [])
        
        formatted_nodes.append(formatted_node)
    
    # Format edges
    formatted_edges = []
    for edge in edges:
        formatted_edge = {
            "src": edge["src"],
            "dst": edge["dst"],
            "type": edge["rel"],
            "metadata": edge["properties"] if edge["properties"] else {}
        }
        formatted_edges.append(formatted_edge)
    
    # Create the export data
    export_data = {
        "schema_version": "0.2",
        "generated_at": datetime.now().isoformat(),
        "pr": {
            "sha": pr_sha,
            "changed_files": changed_files
        },
        "nodes": formatted_nodes,
        "edges": formatted_edges
    }
    
    # Add PR info if available
    if pr_info:
        export_data["pr"].update(pr_info)
    
    return export_data


def sign_file(file_path: Path, key_id: Optional[str] = None) -> Optional[Path]:
    """Sign a file using GPG.

    Args:
        file_path: Path to the file to sign
        key_id: Optional GPG key ID to use for signing

    Returns:
        Path to the signature file, or None if signing failed
    """
    sig_path = Path(f"{file_path}.sig")
    
    try:
        cmd = ["gpg", "--detach-sign"]
        if key_id:
            cmd.extend(["--local-user", key_id])
        cmd.extend(["--output", str(sig_path), str(file_path)])
        
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Signed file {file_path} with GPG")
        return sig_path
    except subprocess.CalledProcessError as e:
        logger.error(f"GPG signing failed: {e.stderr.decode() if e.stderr else str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error signing file: {e}")
        return None


def export_graph(
    db_path: Path,
    repo_path: Path,
    pr_sha: str,
    output_path: Path,
    compress: bool = True,
    sign: bool = False,
    key_id: Optional[str] = None,
    base_branch: str = "main",
) -> Path:
    """Export a relevant slice of the knowledge graph for a PR.

    Args:
        db_path: Path to the database file
        repo_path: Path to the Git repository
        pr_sha: SHA of the PR head commit
        output_path: Path to save the export file
        compress: Whether to compress the output file
        sign: Whether to sign the output file
        key_id: GPG key ID to use for signing
        base_branch: Base branch to compare against

    Returns:
        Path to the exported file

    Raises:
        ExportError: If there's an error exporting the graph
    """
    try:
        # Get the database connection
        conn = ensure_connection(db_path)
        
        # Get the files modified in the PR
        logger.info(f"Getting files modified in PR {pr_sha}")
        modified_files = get_pr_modified_files(repo_path, pr_sha, base_branch)
        logger.info(f"Found {len(modified_files)} modified files")
        
        # Get file nodes for the modified files
        file_nodes = []
        for file_path in modified_files:
            file_id = f"file:{file_path}"
            node = get_node_by_id(conn, file_id)
            if node:
                file_nodes.append(node["id"])
        
        # Get related nodes and edges
        logger.info("Getting related nodes and edges")
        nodes, edges = get_related_nodes(conn, file_nodes, max_hops=1, include_adrs=True)
        logger.info(f"Found {len(nodes)} nodes and {len(edges)} edges")
        
        # Format the export data
        export_data = format_export_data(pr_sha, nodes, edges, modified_files)
        
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
        if sign:
            logger.info("Signing the export file")
            sig_path = sign_file(final_path, key_id)
            if sig_path:
                # Add signature info to the export data
                export_data["sign"] = {
                    "sig_path": str(sig_path)
                }
                if key_id:
                    export_data["sign"]["gpg_fpr"] = key_id
        
        return final_path
    
    except GitError as e:
        raise ExportError(f"Git error: {e}")
    except Exception as e:
        raise ExportError(f"Error exporting graph: {e}")
