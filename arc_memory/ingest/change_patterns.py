"""Change pattern analysis for Arc Memory.

This module provides a plugin for analyzing change patterns over time
in the repository, identifying refactorings, and tracking file evolution.
"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from arc_memory.llm.ollama_client import OllamaClient
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    ChangePatternNode,
    Edge,
    EdgeRel,
    Node,
    NodeType,
)

logger = get_logger(__name__)


class ChangePatternIngestor:
    """Ingestor plugin for analyzing change patterns over time."""

    def __init__(self):
        """Initialize the change pattern ingestor."""
        self.ollama_client = None

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "change_patterns"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return [NodeType.CHANGE_PATTERN, NodeType.REFACTORING]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.FOLLOWS, EdgeRel.PRECEDES, EdgeRel.CORRELATES_WITH]

    def ingest(
        self,
        repo_path: Path,
        last_processed: Optional[Dict[str, Any]] = None,
        llm_enhancement_level: str = "standard",
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest change pattern data from a repository.

        Args:
            repo_path: Path to the repository.
            last_processed: Metadata from the previous run for incremental builds.
            llm_enhancement_level: Level of LLM enhancement to apply.

        Returns:
            A tuple of (nodes, edges, metadata).
        """
        logger.info(f"Ingesting change pattern data from {repo_path}")

        # Initialize Ollama client if needed
        if llm_enhancement_level != "none":
            self.ollama_client = OllamaClient()

        # Get commit history from Git
        commit_history = self._get_commit_history(repo_path)
        if not commit_history:
            logger.warning("No commit history found")
            return [], [], {"error": "No commit history found"}

        # Analyze change patterns
        nodes, edges = self._analyze_change_patterns(commit_history, llm_enhancement_level)

        # Create metadata
        metadata = {
            "pattern_count": len(nodes),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Identified {len(nodes)} change patterns and {len(edges)} relationships")
        return nodes, edges, metadata

    def _get_commit_history(self, repo_path: Path) -> List[Dict[str, Any]]:
        """Get commit history from Git.

        Args:
            repo_path: Path to the repository.

        Returns:
            List of commit data dictionaries.
        """
        try:
            import git
            from git import Repo

            # Open the repository
            repo = Repo(repo_path)

            # Get commits
            commits = []
            for commit in repo.iter_commits(max_count=1000):
                commit_data = {
                    "sha": commit.hexsha,
                    "author": commit.author.name,
                    "message": commit.message,
                    "timestamp": datetime.fromtimestamp(commit.committed_date),
                    "files": list(commit.stats.files.keys()),
                    "insertions": sum(f["insertions"] for f in commit.stats.files.values()),
                    "deletions": sum(f["deletions"] for f in commit.stats.files.values()),
                }
                commits.append(commit_data)

            return commits
        except Exception as e:
            logger.error(f"Error getting commit history: {e}")
            return []

    def _analyze_change_patterns(
        self, commit_history: List[Dict[str, Any]], llm_enhancement_level: str
    ) -> Tuple[List[Node], List[Edge]]:
        """Analyze change patterns in commit history.

        Args:
            commit_history: List of commit data dictionaries.
            llm_enhancement_level: Level of LLM enhancement to apply.

        Returns:
            Tuple of (nodes, edges).
        """
        # Identify co-changing files
        co_change_map = self._identify_co_changing_files(commit_history)

        # Identify refactoring operations
        refactoring_commits = self._identify_refactoring_commits(commit_history)

        # Create nodes and edges
        nodes = []
        edges = []

        # Create change pattern nodes for co-changing files
        for files, frequency in co_change_map.items():
            if frequency < 2 or len(files) < 2:
                continue  # Skip infrequent patterns or single files

            # Convert frozenset to list before slicing
            files_list = list(files)
            
            pattern_id = f"pattern:co_change:{hash(files)}"
            pattern_node = ChangePatternNode(
                id=pattern_id,
                type=NodeType.CHANGE_PATTERN,
                title=f"Co-change Pattern: {', '.join(files_list[:3])}{'...' if len(files_list) > 3 else ''}",
                pattern_type="co_change",
                files=files_list,
                frequency=frequency,
                impact={"files_affected": len(files_list)},
            )
            nodes.append(pattern_node)

            # Create edges to files
            for file_path in files_list:
                file_id = f"file:{file_path}"
                edge = Edge(
                    src=pattern_id,
                    dst=file_id,
                    rel=EdgeRel.CORRELATES_WITH,
                    properties={"frequency": frequency},
                )
                edges.append(edge)

        # Apply LLM enhancements if enabled
        if llm_enhancement_level != "none" and self.ollama_client:
            enhanced_nodes, enhanced_edges = self._enhance_with_llm(
                nodes, edges, commit_history, llm_enhancement_level
            )
            nodes.extend(enhanced_nodes)
            edges.extend(enhanced_edges)

        return nodes, edges

    def _identify_co_changing_files(
        self, commit_history: List[Dict[str, Any]]
    ) -> Dict[frozenset, int]:
        """Identify files that frequently change together.

        Args:
            commit_history: List of commit data dictionaries.

        Returns:
            Dictionary mapping sets of files to frequency.
        """
        co_change_map = defaultdict(int)

        for commit in commit_history:
            files = commit["files"]
            if len(files) >= 2:
                # Create a frozenset of files (immutable, can be used as dict key)
                file_set = frozenset(files)
                co_change_map[file_set] += 1

        return co_change_map

    def _identify_refactoring_commits(
        self, commit_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify commits that likely represent refactoring operations.

        Args:
            commit_history: List of commit data dictionaries.

        Returns:
            List of refactoring commit data.
        """
        refactoring_commits = []

        # Simple heuristic: look for refactoring keywords in commit messages
        refactoring_keywords = [
            "refactor", "restructure", "reorganize", "rewrite", "cleanup", "clean up",
            "simplify", "optimize", "improve", "enhance", "modernize"
        ]

        for commit in commit_history:
            message = commit["message"].lower()
            if any(keyword in message for keyword in refactoring_keywords):
                refactoring_commits.append(commit)

        return refactoring_commits

    def _enhance_with_llm(
        self,
        nodes: List[Node],
        edges: List[Edge],
        commit_history: List[Dict[str, Any]],
        enhancement_level: str,
    ) -> Tuple[List[Node], List[Edge]]:
        """Enhance change pattern analysis with LLM.

        Args:
            nodes: Existing pattern nodes.
            edges: Existing pattern edges.
            commit_history: List of commit data dictionaries.
            enhancement_level: Level of enhancement to apply.

        Returns:
            Additional nodes and edges from LLM analysis.
        """
        if not self.ollama_client:
            return [], []

        logger.info(f"Enhancing change pattern analysis with LLM ({enhancement_level} level)")

        # This is a placeholder implementation
        # In a real implementation, we would use the LLM to analyze commit messages
        # and identify more complex patterns

        return [], []
