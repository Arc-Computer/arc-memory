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
USER_AGENT = "Arc-Memory/0.2.2"


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

            # Initialize the GitHub fetcher
            from arc_memory.ingest.github_fetcher import GitHubFetcher
            fetcher = GitHubFetcher(github_token)

            # Get PRs
            pr_nodes = []
            pr_edges = []

            # Determine if we need to do an incremental build
            since = None
            if last_processed and "timestamp" in last_processed:
                try:
                    since = datetime.fromisoformat(last_processed["timestamp"])
                    logger.info(f"Performing incremental build since {since.isoformat()}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid timestamp in last_processed: {e}")

            try:
                # Fetch PRs
                logger.info(f"Fetching PRs for {owner}/{repo}")
                prs = fetcher.fetch_pull_requests_sync(owner, repo, since)
                logger.info(f"Fetched {len(prs)} PRs")

                # Get issues (needed for mention edges)
                logger.info(f"Fetching issues for {owner}/{repo}")
                issues = fetcher.fetch_issues_sync(owner, repo, since)
                logger.info(f"Fetched {len(issues)} issues")

                # Process each PR
                for pr in prs:
                    try:
                        # Fetch additional PR details
                        pr_number = pr["number"]
                        logger.info(f"Fetching details for PR #{pr_number}")
                        pr_details = fetcher.fetch_pr_details_sync(owner, repo, pr_number)

                        # Create PR node
                        pr_node = fetcher.create_pr_node(pr, pr_details)
                        pr_nodes.append(pr_node)

                        # Create mention edges from PR body
                        if pr["body"]:
                            mention_edges = fetcher.create_mention_edges(
                                pr_node.id, pr["body"], issues, prs
                            )
                            pr_edges.extend(mention_edges)

                        # Create mention edges from PR comments
                        if pr_details.get("comments"):
                            for comment in pr_details["comments"]:
                                if comment.get("body"):
                                    comment_mention_edges = fetcher.create_mention_edges(
                                        pr_node.id, comment["body"], issues, prs
                                    )
                                    pr_edges.extend(comment_mention_edges)

                        # Create MERGES edge if PR has a merge commit
                        if pr_node.merged_commit_sha:
                            pr_edges.append(
                                Edge(
                                    src=pr_node.id,
                                    dst=pr_node.merged_commit_sha,
                                    rel=EdgeRel.MERGES,
                                    properties={"merged_at": pr_node.merged_at.isoformat() if pr_node.merged_at else None},
                                )
                            )
                    except Exception as e:
                        logger.error(f"Error processing PR #{pr['number']}: {e}")
                        # Continue with the next PR

                # Get issues
                issue_nodes = []
                issue_edges = []

                # Process each issue
                for issue in issues:
                    try:
                        # Fetch additional issue details
                        issue_number = issue["number"]
                        logger.info(f"Fetching details for issue #{issue_number}")
                        issue_details = fetcher.fetch_issue_details_sync(owner, repo, issue_number)

                        # Create issue node
                        issue_node = fetcher.create_issue_node(issue, issue_details)
                        issue_nodes.append(issue_node)

                        # Create mention edges from issue body
                        if issue["body"]:
                            mention_edges = fetcher.create_mention_edges(
                                issue_node.id, issue["body"], issues, prs
                            )
                            issue_edges.extend(mention_edges)

                        # Create mention edges from issue comments
                        if issue_details.get("comments"):
                            for comment in issue_details["comments"]:
                                if comment.get("body"):
                                    comment_mention_edges = fetcher.create_mention_edges(
                                        issue_node.id, comment["body"], issues, prs
                                    )
                                    issue_edges.extend(comment_mention_edges)
                    except Exception as e:
                        logger.error(f"Error processing issue #{issue['number']}: {e}")
                        # Continue with the next issue
            except Exception as e:
                logger.error(f"Error fetching GitHub data: {e}")
                # Return empty results but don't fail the build
                return [], [], {
                    "error": f"Error fetching GitHub data: {e}",
                    "timestamp": datetime.now().isoformat(),
                    "message": "GitHub data not fully included due to an error."
                }

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
