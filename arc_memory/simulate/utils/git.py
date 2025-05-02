"""Git utilities for Arc Memory simulation.

This module provides utilities for working with Git repositories.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

from git import Repo

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def get_repo_path(repo_path: Optional[str] = None) -> Path:
    """Get the path to the Git repository.
    
    Args:
        repo_path: Optional path to the repository
        
    Returns:
        Path to the repository
        
    Raises:
        ValueError: If the repository path is invalid
    """
    if repo_path:
        path = Path(repo_path)
        if not path.exists():
            raise ValueError(f"Repository path does not exist: {path}")
        return path
    
    # Use current directory if repo_path is not provided
    return Path.cwd()


def parse_rev_range(rev_range: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a Git revision range.
    
    Args:
        rev_range: Git revision range (e.g., "HEAD~1..HEAD")
        
    Returns:
        A tuple of (start_rev, end_rev)
    """
    if ".." in rev_range:
        parts = rev_range.split("..")
        if len(parts) == 2:
            return parts[0], parts[1]
    
    # If the range doesn't contain "..", assume it's a single commit
    return None, rev_range


def get_repo(repo_path: Optional[str] = None) -> Repo:
    """Get a Git repository.
    
    Args:
        repo_path: Optional path to the repository
        
    Returns:
        A Git repository
        
    Raises:
        ValueError: If the repository path is invalid
    """
    try:
        path = get_repo_path(repo_path)
        return Repo(path)
    except Exception as e:
        logger.error(f"Error getting Git repository: {e}")
        raise ValueError(f"Error getting Git repository: {e}")


def ensure_arc_dir() -> Path:
    """Ensure the .arc directory exists.
    
    Returns:
        Path to the .arc directory
    """
    arc_dir = Path.home() / ".arc"
    arc_dir.mkdir(exist_ok=True)
    return arc_dir
