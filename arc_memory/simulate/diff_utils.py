"""Diff analysis utilities for Arc Memory simulation.

This module provides functions for analyzing Git diffs to identify affected files
and services for simulation.
"""

import json
import os
import subprocess
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

import git
from git import Repo

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def serialize_diff(rev_range: str, repo_path: Optional[Path] = None) -> Dict[str, Any]:
    """Extract diff from Git using the provided rev-range.

    Args:
        rev_range: Git rev-range (e.g., "HEAD~1..HEAD")
        repo_path: Path to the Git repository (defaults to current directory)

    Returns:
        A dictionary containing the serialized diff information

    Raises:
        GitError: If there's an error accessing the Git repository
    """
    try:
        # Use current directory if repo_path is not provided
        if repo_path is None:
            repo_path = Path.cwd()

        # Open the repository
        repo = Repo(repo_path)

        # Parse the rev-range
        start_rev, end_rev = parse_rev_range(rev_range)

        # Get the commits in the range
        if start_rev and end_rev:
            commit_range = f"{start_rev}..{end_rev}"
            commits = list(repo.iter_commits(commit_range))
        else:
            # Default to HEAD if range parsing fails
            commits = [repo.head.commit]

        if not commits:
            logger.warning(f"No commits found in range: {rev_range}")
            return {
                "files": [],
                "commit_count": 0,
                "range": rev_range,
                "timestamp": datetime.datetime.now().isoformat()
            }

        # Get the diff for each commit
        files_changed = set()
        insertions_total = 0
        deletions_total = 0
        file_stats = {}

        for commit in commits:
            # Get the parent commit (or None if this is the first commit)
            parents = commit.parents
            if not parents:
                # Initial commit - compare with empty tree
                diff_index = commit.diff(git.NULL_TREE)
            else:
                # Normal commit - compare with first parent
                diff_index = commit.diff(parents[0])

            # Process each changed file
            for diff in diff_index:
                if diff.a_path:
                    path = diff.a_path
                elif diff.b_path:
                    path = diff.b_path
                else:
                    continue

                files_changed.add(path)

                # Get stats for this file
                if path not in file_stats:
                    file_stats[path] = {
                        "insertions": 0,
                        "deletions": 0,
                        "status": "modified"
                    }

                # Update status based on diff type
                if diff.new_file:
                    file_stats[path]["status"] = "added"
                elif diff.deleted_file:
                    file_stats[path]["status"] = "deleted"
                elif diff.renamed:
                    file_stats[path]["status"] = "renamed"

                # Get insertions and deletions if available
                if path in commit.stats.files:
                    stats = commit.stats.files[path]
                    file_stats[path]["insertions"] += stats.get("insertions", 0)
                    file_stats[path]["deletions"] += stats.get("deletions", 0)
                    insertions_total += stats.get("insertions", 0)
                    deletions_total += stats.get("deletions", 0)

        # Create the result dictionary
        result = {
            "files": [
                {
                    "path": path,
                    "insertions": stats["insertions"],
                    "deletions": stats["deletions"],
                    "status": stats["status"]
                }
                for path, stats in file_stats.items()
            ],
            "commit_count": len(commits),
            "range": rev_range,
            "start_commit": commits[-1].hexsha if commits else None,
            "end_commit": commits[0].hexsha if commits else None,
            "timestamp": datetime.datetime.now().isoformat(),
            "stats": {
                "files_changed": len(files_changed),
                "insertions": insertions_total,
                "deletions": deletions_total
            }
        }

        return result

    except git.exc.GitCommandError as e:
        logger.error(f"Git command error: {e}")
        raise GitError(f"Git command error: {e}")
    except git.exc.InvalidGitRepositoryError:
        logger.error(f"{repo_path} is not a valid Git repository")
        raise GitError(f"{repo_path} is not a valid Git repository")
    except Exception as e:
        logger.exception("Unexpected error during diff serialization")
        raise GitError(f"Failed to serialize diff: {e}")


def parse_rev_range(rev_range: str) -> tuple[Optional[str], Optional[str]]:
    """Parse a Git revision range.

    Args:
        rev_range: Git rev-range (e.g., "HEAD~1..HEAD")

    Returns:
        A tuple of (start_rev, end_rev)
    """
    if ".." in rev_range:
        parts = rev_range.split("..")
        if len(parts) == 2:
            return parts[0], parts[1]

    # If the range doesn't contain "..", assume it's a single commit
    return None, rev_range


def load_diff_from_file(diff_path: Path) -> Dict[str, Any]:
    """Load a pre-serialized diff from a JSON file.

    Args:
        diff_path: Path to the diff JSON file

    Returns:
        A dictionary containing the serialized diff information

    Raises:
        FileNotFoundError: If the diff file doesn't exist
        JSONDecodeError: If the diff file contains invalid JSON
    """
    try:
        with open(diff_path, 'r') as f:
            diff_data = json.load(f)

        # Validate the diff data
        if not isinstance(diff_data, dict) or "files" not in diff_data:
            raise ValueError("Invalid diff format: missing 'files' key")

        return diff_data

    except FileNotFoundError:
        logger.error(f"Diff file not found: {diff_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in diff file: {e}")
        raise
    except Exception as e:
        logger.exception("Unexpected error loading diff file")
        raise ValueError(f"Failed to load diff file: {e}")


def analyze_diff(diff: Dict[str, Any], causal_db: str) -> List[str]:
    """Identify affected files and services from a diff.

    Args:
        diff: Serialized diff information
        causal_db: Path to the causal graph database

    Returns:
        A list of affected service names
    """
    from arc_memory.simulate.causal import derive_causal
    from arc_memory.simulate.causal import get_affected_services

    # Extract the list of changed files
    changed_files = [file["path"] for file in diff.get("files", [])]

    try:
        # Derive the causal graph from the database
        causal_graph = derive_causal(causal_db)

        # Get affected services
        affected_services = get_affected_services(causal_graph, changed_files)

        # If no services were found, fall back to the simple mapping
        if not affected_services:
            affected_services = list(map_files_to_services(changed_files))

        return affected_services

    except Exception as e:
        # Log the error and fall back to the simple mapping
        logger.error(f"Error analyzing diff with causal graph: {e}")
        return list(map_files_to_services(changed_files))


def map_files_to_services(files: List[str]) -> Set[str]:
    """Map files to services based on file extensions and paths.

    This is a simple implementation that will be replaced with causal graph analysis.

    Args:
        files: List of file paths

    Returns:
        A set of service names
    """
    services = set()

    for file in files:
        # Extract file extension
        _, ext = os.path.splitext(file)
        ext = ext.lower()

        # Map based on file path patterns
        if "api" in file.lower() or "rest" in file.lower():
            services.add("api-service")
        elif "db" in file.lower() or "sql" in file.lower() or "database" in file.lower():
            services.add("database-service")
        elif "auth" in file.lower() or "login" in file.lower():
            services.add("auth-service")
        elif "user" in file.lower() or "account" in file.lower():
            services.add("user-service")
        elif "payment" in file.lower() or "billing" in file.lower():
            services.add("payment-service")

        # Map based on file extensions
        if ext in [".py", ".ipynb"]:
            services.add("python-service")
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            services.add("frontend-service")
        elif ext in [".java", ".kt", ".scala"]:
            services.add("jvm-service")
        elif ext in [".go"]:
            services.add("go-service")
        elif ext in [".rb"]:
            services.add("ruby-service")
        elif ext in [".php"]:
            services.add("php-service")
        elif ext in [".rs"]:
            services.add("rust-service")
        elif ext in [".c", ".cpp", ".h", ".hpp"]:
            services.add("cpp-service")
        elif ext in [".yaml", ".yml", ".json", ".toml"]:
            services.add("config-service")
        elif ext in [".md", ".txt", ".rst"]:
            services.add("docs-service")

    # If no specific service was identified, use a generic service
    if not services:
        services.add("unknown-service")

    return services


class GitError(Exception):
    """Exception raised for Git-related errors."""
    pass
