"""Change pattern analysis for Arc Memory.

This module provides a plugin for analyzing change patterns over time
in the repository, identifying refactorings, and tracking file evolution.
"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Removed Ollama import to ensure only OpenAI is used
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    ChangePatternNode,
    Edge,
    EdgeRel,
    Node,
    NodeType,
)

# Import OpenAI client conditionally to avoid hard dependency
try:
    from arc_memory.llm.openai_client import OpenAIClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = get_logger(__name__)


class ChangePatternIngestor:
    """Ingestor plugin for analyzing change patterns over time."""

    def __init__(self):
        """Initialize the change pattern ingestor."""
        self.openai_client = None
        self.llm_provider = "openai"  # Always use OpenAI

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
        ollama_client: Optional[Any] = None,  # Kept for backward compatibility
        openai_client: Optional[Any] = None,
        llm_provider: str = "openai",  # Always use OpenAI
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest change pattern data from a repository.

        Args:
            repo_path: Path to the repository.
            last_processed: Metadata from the previous run for incremental builds.
            llm_enhancement_level: Level of LLM enhancement to apply.
            ollama_client: Optional Ollama client (ignored, kept for backward compatibility).
            openai_client: Optional OpenAI client for LLM processing.
            llm_provider: The LLM provider to use (only "openai" is supported).

        Returns:
            A tuple of (nodes, edges, metadata).
        """
        logger.info(f"Ingesting change pattern data from {repo_path}")

        # Set LLM clients and provider - only use OpenAI
        if llm_enhancement_level != "none":
            self.llm_provider = "openai"  # Force OpenAI
            if openai_client is not None:
                self.openai_client = openai_client

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

        # Apply LLM enhancements if enabled - only use OpenAI
        if llm_enhancement_level != "none" and self.openai_client:
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
        # Check if we have a valid OpenAI client
        if not self.openai_client:
            return [], []

        logger.info(f"Enhancing change pattern analysis with OpenAI GPT-4.1 ({enhancement_level} level)")

        # OpenAI-specific implementation
        enhanced_nodes = []
        enhanced_edges = []

        # Process each pattern node with OpenAI
        for pattern_node in nodes:
            if pattern_node.type == NodeType.CHANGE_PATTERN:
                # Create a description of the pattern for the LLM
                pattern = f"Pattern: {pattern_node.title}\n"
                pattern += f"Files: {', '.join(pattern_node.files)}\n"
                pattern += f"Frequency: {pattern_node.frequency} occurrences\n"

                # Use OpenAI to enhance the pattern description
                try:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4.1",
                        messages=[
                            {"role": "system", "content": """You are a specialized software engineering assistant that analyzes code change patterns.
Your task is to analyze patterns of files that change together and provide insights about:
1. The likely architectural relationship between these files
2. Potential coupling issues or dependencies
3. Suggestions for improving the codebase organization
4. Possible refactoring opportunities

Be specific, concise, and focus on actionable insights."""},
                            {"role": "user", "content": f"Analyze and enhance the following change pattern:\n{pattern}"}
                        ],
                        temperature=0.3,
                        max_tokens=1000
                    )

                    enhanced_description = response.choices[0].message.content.strip()

                    # Create a new node with the enhanced description
                    enhanced_node_id = f"{pattern_node.id}:enhanced"
                    enhanced_node = ChangePatternNode(
                        id=enhanced_node_id,
                        type=NodeType.CHANGE_PATTERN,
                        title=f"Enhanced {pattern_node.title}",
                        pattern_type="enhanced_co_change",
                        files=pattern_node.files,
                        frequency=pattern_node.frequency,
                        impact=pattern_node.impact,
                        description=enhanced_description,
                        confidence=0.8
                    )
                    enhanced_nodes.append(enhanced_node)

                    # Create an edge from the original pattern to the enhanced one
                    edge = Edge(
                        src=pattern_node.id,
                        dst=enhanced_node_id,
                        rel=EdgeRel.CORRELATES_WITH,
                        properties={"enhancement": "llm_analysis"}
                    )
                    enhanced_edges.append(edge)
                except Exception as e:
                    logger.error(f"Error enhancing pattern with OpenAI: {e}")

        return enhanced_nodes, enhanced_edges
