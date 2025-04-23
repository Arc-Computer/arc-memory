"""Git ingestion for Arc Memory."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import git
from git import Repo

from arc_memory.errors import GitError, IngestError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import CommitNode, Edge, EdgeRel, FileNode, Node, NodeType

logger = get_logger(__name__)


class GitIngestor:
    """Ingestor plugin for Git repositories."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "git"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return [NodeType.COMMIT, NodeType.FILE]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MODIFIES]

    def ingest(
        self,
        repo_path: Path,
        max_commits: int = 5000,
        days: int = 365,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest Git data from a repository.

        Args:
            repo_path: Path to the Git repository.
            max_commits: Maximum number of commits to process.
            days: Maximum age of commits to process in days.
            last_processed: Metadata from the previous run for incremental builds.

        Returns:
            A tuple of (nodes, edges, metadata).

        Raises:
            GitError: If there's an error accessing the Git repository.
            IngestError: If there's an error during ingestion.
        """
        logger.info(f"Ingesting Git data from {repo_path}")
        logger.info(f"Max commits: {max_commits}, Max days: {days}")

        # Extract last commit hash from last_processed metadata
        last_commit_hash = None
        if last_processed and "last_commit_hash" in last_processed:
            last_commit_hash = last_processed["last_commit_hash"]
            logger.info(f"Incremental build from commit {last_commit_hash}")

        try:
            # Open the repository
            repo = Repo(repo_path)

            # Get commits
            if last_commit_hash:
                # Incremental: Get commits since last processed commit
                try:
                    # Make sure the commit exists in the repo
                    repo.commit(last_commit_hash)
                    commit_range = f"{last_commit_hash}..HEAD"
                    commits = list(repo.iter_commits(commit_range, max_count=max_commits))
                except git.exc.GitCommandError:
                    logger.warning(f"Commit {last_commit_hash} not found, falling back to full build")
                    commits = list(repo.iter_commits(max_count=max_commits))
            else:
                # Full build: Get commits with limits
                since_date = datetime.now() - timedelta(days=days)
                commits = list(repo.iter_commits(max_count=max_commits, since=since_date))

            logger.info(f"Processing {len(commits)} commits")

            # Process commits
            nodes = []
            edges = []
            file_nodes = {}

            for commit in commits:
                # Create commit node
                commit_node = CommitNode(
                    id=f"commit:{commit.hexsha}",
                    type=NodeType.COMMIT,
                    title=commit.summary,
                    body=commit.message,
                    ts=datetime.fromtimestamp(commit.committed_date),
                    author=commit.author.name,
                    files=list(commit.stats.files.keys()),
                    sha=commit.hexsha,
                )
                nodes.append(commit_node)

                # Create File nodes and edges to modified files
                for file_path in commit.stats.files:
                    file_id = f"file:{file_path}"

                    # Create File node if it doesn't exist yet
                    if file_id not in file_nodes:
                        try:
                            # Try to get the file's last modification time
                            file_full_path = repo_path / file_path
                            if file_full_path.exists():
                                last_modified = datetime.fromtimestamp(file_full_path.stat().st_mtime)
                            else:
                                last_modified = None

                            # Try to determine the language based on file extension
                            _, ext = os.path.splitext(file_path)
                            language = ext[1:] if ext else None

                            file_node = FileNode(
                                id=file_id,
                                type=NodeType.FILE,
                                title=os.path.basename(file_path),
                                path=file_path,
                                language=language,
                                last_modified=last_modified,
                                ts=last_modified,
                            )
                            nodes.append(file_node)
                            file_nodes[file_id] = file_node
                        except Exception as e:
                            logger.warning(f"Failed to create File node for {file_path}: {e}")

                    # Create edge from commit to file
                    edge = Edge(
                        src=commit_node.id,
                        dst=file_id,
                        rel=EdgeRel.MODIFIES,
                        properties={
                            "insertions": commit.stats.files[file_path]["insertions"],
                            "deletions": commit.stats.files[file_path]["deletions"],
                        },
                    )
                    edges.append(edge)

            # Create metadata
            metadata = {
                "commit_count": len(commits),
                "last_commit_hash": commits[0].hexsha if commits else last_commit_hash,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Processed {len(nodes)} commit nodes and {len(edges)} edges")
            return nodes, edges, metadata
        except git.exc.GitCommandError as e:
            logger.error(f"Git command error: {e}")
            raise GitError(f"Git command error: {e}")
        except git.exc.InvalidGitRepositoryError:
            logger.error(f"{repo_path} is not a valid Git repository")
            raise GitError(f"{repo_path} is not a valid Git repository")
        except Exception as e:
            logger.exception("Unexpected error during Git ingestion")
            raise IngestError(f"Failed to ingest Git data: {e}")


# For backward compatibility
def ingest_git(
    repo_path: Path,
    max_commits: int = 5000,
    days: int = 365,
    last_commit_hash: Optional[str] = None,
) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
    """Ingest Git data from a repository.

    This function is maintained for backward compatibility.
    New code should use the GitIngestor class directly.

    Args:
        repo_path: Path to the Git repository.
        max_commits: Maximum number of commits to process.
        days: Maximum age of commits to process in days.
        last_commit_hash: The hash of the last processed commit for incremental builds.

    Returns:
        A tuple of (nodes, edges, metadata).
    """
    last_processed = None
    if last_commit_hash:
        last_processed = {"last_commit_hash": last_commit_hash}

    ingestor = GitIngestor()
    return ingestor.ingest(repo_path, max_commits, days, last_processed)
