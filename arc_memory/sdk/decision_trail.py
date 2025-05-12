"""Decision Trail API for Arc Memory SDK.

This module provides methods for tracing the history of specific file lines
and extracting decision rationales.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from arc_memory.db.base import DatabaseAdapter
from arc_memory.logging_conf import get_logger
from arc_memory.sdk.cache import cached
from arc_memory.sdk.errors import QueryError
from arc_memory.sdk.models import DecisionTrailEntry, EntityDetails
from arc_memory.sdk.progress import ProgressCallback, ProgressStage
from arc_memory.trace import trace_history_for_file_line

logger = get_logger(__name__)


@cached()
def get_decision_trail(
    adapter: DatabaseAdapter,
    file_path: str,
    line_number: int,
    max_results: int = 5,
    max_hops: int = 3,
    include_rationale: bool = True,
    callback: Optional[ProgressCallback] = None
) -> List[DecisionTrailEntry]:
    """Get the decision trail for a specific line in a file.

    This method traces the history of a specific line in a file, showing the commit
    that last modified it and related entities such as PRs, issues, and ADRs. It's
    particularly useful for understanding why a particular piece of code exists.

    Args:
        adapter: The database adapter to use.
        file_path: Path to the file, relative to the repository root.
        line_number: Line number to trace (1-based).
        max_results: Maximum number of results to return.
        max_hops: Maximum number of hops in the graph traversal.
        include_rationale: Whether to extract decision rationales.
        callback: Optional callback for progress reporting.

    Returns:
        A list of DecisionTrailEntry objects representing the decision trail.

    Raises:
        QueryError: If getting the decision trail fails.
    """
    try:
        # Report progress
        if callback:
            callback(
                ProgressStage.INITIALIZING,
                "Initializing decision trail analysis",
                0.0
            )

        # Get the database path
        db_path = Path(adapter.db_path) if hasattr(adapter, "db_path") else None
        if not db_path:
            raise QueryError("Database path not available")

        # Report progress
        if callback:
            callback(
                ProgressStage.QUERYING,
                "Tracing file line history",
                0.2
            )

        # Trace the history
        results = trace_history_for_file_line(
            db_path=db_path,
            file_path=file_path,
            line_number=line_number,
            max_results=max_results,
            max_hops=max_hops
        )

        # Report progress
        if callback:
            callback(
                ProgressStage.PROCESSING,
                "Processing decision trail results",
                0.6
            )

        # Convert to DecisionTrailEntry models
        entities = []
        for i, result in enumerate(results):
            # Extract basic properties
            entity = DecisionTrailEntry(
                id=result["id"],
                type=result["type"],
                title=result.get("title", ""),
                body=result.get("body", ""),
                timestamp=result.get("timestamp"),
                properties={
                    k: v for k, v in result.items()
                    if k not in ["id", "type", "title", "body", "timestamp"]
                },
                related_entities=[],
                rationale=_extract_rationale(result) if include_rationale else None,
                importance=_calculate_importance(result),
                trail_position=i
            )
            entities.append(entity)

        # Report progress
        if callback:
            callback(
                ProgressStage.COMPLETING,
                "Decision trail analysis complete",
                1.0
            )

        return entities

    except Exception as e:
        logger.exception(f"Error in get_decision_trail: {e}")
        raise QueryError(f"Failed to get decision trail: {e}")


def _extract_rationale(node: Dict[str, Any]) -> Optional[str]:
    """Extract a decision rationale from a node.

    This function attempts to extract a rationale from the node's body or properties.
    It looks for keywords like "because", "reason", "rationale", etc.

    Args:
        node: The node to extract a rationale from.

    Returns:
        The extracted rationale, or None if no rationale could be extracted.
    """
    # This is a simplified implementation that would be enhanced in a real system
    body = node.get("body", "")
    if not body:
        return None

    # Look for common rationale indicators
    rationale_indicators = [
        "because", "reason", "rationale", "due to", "in order to",
        "to fix", "to address", "to resolve", "to implement"
    ]

    for indicator in rationale_indicators:
        if indicator in body.lower():
            # Find the sentence containing the indicator
            sentences = body.split(". ")
            for sentence in sentences:
                if indicator in sentence.lower():
                    return sentence.strip()

    # If no specific rationale found, return the first sentence as a fallback
    sentences = body.split(". ")
    if sentences:
        return sentences[0].strip()

    return None


def _calculate_importance(node: Dict[str, Any]) -> float:
    """Calculate an importance score for a node in the decision trail.

    This function calculates an importance score based on the node type,
    content, and other factors.

    Args:
        node: The node to calculate importance for.

    Returns:
        An importance score between 0.0 and 1.0.
    """
    # This is a simplified implementation that would be enhanced in a real system
    node_type = node.get("type", "")
    
    # Base importance by node type
    base_importance = {
        "adr": 0.9,      # ADRs are highly important
        "issue": 0.7,    # Issues are quite important
        "pr": 0.6,       # PRs are moderately important
        "commit": 0.5,   # Commits are somewhat important
        "file": 0.3      # Files are less important
    }.get(node_type, 0.5)
    
    # Adjust based on content
    body = node.get("body", "")
    title = node.get("title", "")
    
    # Keywords that indicate importance
    importance_keywords = [
        "critical", "important", "significant", "major", "key",
        "breaking", "security", "vulnerability", "fix", "bug"
    ]
    
    # Check for keywords in title and body
    keyword_bonus = 0.0
    for keyword in importance_keywords:
        if keyword in (title + " " + body).lower():
            keyword_bonus += 0.05
    
    # Cap the bonus at 0.3
    keyword_bonus = min(keyword_bonus, 0.3)
    
    # Calculate final importance
    importance = base_importance + keyword_bonus
    
    # Ensure the result is between 0.0 and 1.0
    return max(0.0, min(1.0, importance))
