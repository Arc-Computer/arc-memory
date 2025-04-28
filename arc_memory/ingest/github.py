"""GitHub ingestion for Arc Memory."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import git
import requests
from git import Repo

from arc_memory.auth.github import get_github_token, get_installation_token_for_repo
from arc_memory.errors import GitHubAuthError, IngestError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, IssueNode, NodeType, PRNode

logger = get_logger(__name__)

# Constants
GITHUB_API_URL = "https://api.github.com"
USER_AGENT = "Arc-Memory/0.2.1"


def get_repo_info(repo_path: Path) -> Tuple[str, str]:
    """Get the owner and name of a GitHub repository.

    Args:
        repo_path: Path to the Git repository.

    Returns:
        A tuple of (owner, repo).

    Raises:
        IngestError: If the repository info couldn't be determined.
    """
    try:
        repo = Repo(repo_path)
        remotes = list(repo.remotes)
        if not remotes:
            raise IngestError("No remotes found in repository")

        # Try to find a GitHub remote
        github_remote = None
        for remote in remotes:
            for url in remote.urls:
                if "github.com" in url:
                    github_remote = url
                    break
            if github_remote:
                break

        if not github_remote:
            # Use the first remote
            github_remote = next(remotes[0].urls)

        # Parse owner and repo from remote URL
        # Handle different URL formats:
        # - https://github.com/owner/repo.git
        # - git@github.com:owner/repo.git
        match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", github_remote)
        if not match:
            raise IngestError(f"Could not parse GitHub repository from remote URL: {github_remote}")

        owner = match.group(1)
        repo = match.group(2)
        return owner, repo
    except git.exc.GitCommandError as e:
        logger.error(f"Git command error: {e}")
        raise IngestError(f"Git command error: {e}")
    except git.exc.InvalidGitRepositoryError:
        logger.error(f"{repo_path} is not a valid Git repository")
        raise IngestError(f"{repo_path} is not a valid Git repository")
    except Exception as e:
        logger.exception("Unexpected error getting repository info")
        raise IngestError(f"Failed to get repository info: {e}")


class GitHubIngestor:
    """Ingestor plugin for GitHub repositories."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "github"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return [NodeType.PR, NodeType.ISSUE]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MENTIONS, EdgeRel.MERGES]

    def ingest(
        self,
        repo_path: Path,
        token: Optional[str] = None,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Any], List[Edge], Dict[str, Any]]:
        """Ingest GitHub data for a repository.

        Args:
            repo_path: Path to the Git repository.
            token: GitHub token to use for API calls.
            last_processed: Metadata from the last build for incremental processing.

        Returns:
            A tuple of (nodes, edges, metadata).

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error during ingestion.
        """
        logger.info(f"Ingesting GitHub data for repository at {repo_path}")
        if last_processed:
            logger.info("Performing incremental build")

        try:
            # Get repository owner and name
            owner, repo = get_repo_info(repo_path)
            logger.info(f"Repository: {owner}/{repo}")

            # Get GitHub token with fallback
            # Try to get an installation token first
            installation_token = get_installation_token_for_repo(owner, repo)
            if installation_token:
                logger.info(f"Using GitHub App installation token for {owner}/{repo}")
                github_token = installation_token
            else:
                # Fall back to personal access token, allowing failure
                github_token = get_github_token(token, allow_failure=True)
                if github_token:
                    logger.info("Using personal access token")
                else:
                    logger.warning("No GitHub token found. GitHub data will not be included in the graph.")
                    logger.warning("To include GitHub data, run 'arc auth gh' to authenticate with GitHub.")
                    # Return empty results but don't fail the build
                    return [], [], {
                        "error": "No GitHub token found",
                        "timestamp": datetime.now().isoformat(),
                        "message": "GitHub data not included. Run 'arc auth gh' to authenticate."
                    }

            # Set up API headers
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": USER_AGENT,
            }

            # Get PRs
            pr_nodes = []
            pr_edges = []

            # In a real implementation, we would:
            # 1. Fetch PRs from GitHub API
            # 2. For incremental builds, use the since parameter
            # 3. Create PR nodes and edges
            # 4. Handle pagination

            # For now, we'll just return empty lists
            logger.info("GitHub ingestion not fully implemented yet")
            logger.info("Returning empty lists")

            # Get issues
            issue_nodes = []
            issue_edges = []

            # In a real implementation, we would:
            # 1. Fetch issues from GitHub API
            # 2. For incremental builds, use the since parameter
            # 3. Create issue nodes and edges
            # 4. Handle pagination

            # Combine nodes and edges
            nodes = pr_nodes + issue_nodes
            edges = pr_edges + issue_edges

            # Create metadata
            metadata = {
                "pr_count": len(pr_nodes),
                "issue_count": len(issue_nodes),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Processed {len(nodes)} GitHub nodes and {len(edges)} edges")
            return nodes, edges, metadata
        except GitHubAuthError:
            # Re-raise GitHubAuthError
            raise
        except Exception as e:
            logger.exception("Unexpected error during GitHub ingestion")
            raise IngestError(f"Failed to ingest GitHub data: {e}")


# For backward compatibility
def ingest_github(
    repo_path: Path,
    token: Optional[str] = None,
    last_processed: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Any], List[Edge], Dict[str, Any]]:
    """Ingest GitHub data for a repository.

    This function is maintained for backward compatibility.
    New code should use the GitHubIngestor class directly.

    Args:
        repo_path: Path to the Git repository.
        token: GitHub token to use for API calls.
        last_processed: Metadata from the last build for incremental processing.

    Returns:
        A tuple of (nodes, edges, metadata).
    """
    ingestor = GitHubIngestor()
    return ingestor.ingest(repo_path, token, last_processed)
