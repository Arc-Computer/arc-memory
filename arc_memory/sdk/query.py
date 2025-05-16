"""Query API for Arc Memory SDK.

This module provides methods for querying the knowledge graph using natural language.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from arc_memory.db.base import DatabaseAdapter
from arc_memory.logging_conf import get_logger
from arc_memory.sdk.cache import cached
from arc_memory.sdk.errors import QueryError
from arc_memory.sdk.models import QueryResult
from arc_memory.sdk.progress import ProgressCallback, ProgressStage
from arc_memory.semantic_search import process_query

logger = get_logger(__name__)


@cached()
def query_knowledge_graph(
    adapter: DatabaseAdapter,
    question: str,
    max_results: int = 5,
    max_hops: int = 3,
    include_causal: bool = True,
    callback: Optional[ProgressCallback] = None,
    timeout: int = 60,
    repo_ids: Optional[List[str]] = None
) -> QueryResult:
    """Query the knowledge graph using natural language.

    This method enables natural language queries about the codebase, focusing on
    causal relationships and decision trails. It's particularly useful for understanding
    why certain changes were made and their implications.

    Args:
        adapter: The database adapter to use.
        question: The natural language question to ask.
        max_results: Maximum number of results to return.
        max_hops: Maximum number of hops in the graph traversal.
        include_causal: Whether to prioritize causal relationships.
        callback: Optional callback for progress reporting.
        timeout: Maximum time in seconds to wait for Ollama response.
        repo_ids: Optional list of repository IDs to filter by.

    Returns:
        A QueryResult containing the answer and supporting evidence.

    Raises:
        QueryError: If the query fails.

    Note:
        This method requires Ollama to be installed and running. If Ollama is not
        available, it will return an error message with installation instructions.
    """
    try:
        # Report progress
        if callback:
            callback(
                ProgressStage.INITIALIZING,
                "Initializing query processing",
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
                "Processing natural language query",
                0.2
            )

        # Process the query
        result = process_query(
            db_path=db_path,
            query=question,
            max_results=max_results,
            max_hops=max_hops,
            timeout=timeout,
            repo_ids=repo_ids
        )

        # Report progress
        if callback:
            callback(
                ProgressStage.COMPLETING,
                "Query processing complete",
                1.0
            )

        # Check for errors
        if "error" in result:
            raise QueryError(result["error"])

        # Convert to QueryResult model
        # Normalize confidence score from 1-10 scale to 0.0-1.0 scale
        confidence = result.get("confidence", 0.0)
        if isinstance(confidence, (int, float)) and confidence > 0:
            normalized_confidence = min(confidence / 10.0, 1.0)
        else:
            normalized_confidence = 0.0

        return QueryResult(
            query=question,
            answer=result.get("answer", ""),
            confidence=normalized_confidence,  # Normalized to 0.0-1.0 scale
            evidence=result.get("results", []),
            query_understanding=result.get("understanding", ""),
            reasoning=result.get("reasoning", ""),
            execution_time=result.get("execution_time", 0.0)
        )

    except Exception as e:
        logger.exception(f"Error in query_knowledge_graph: {e}")

        # Provide more specific error messages based on the type of exception
        if "No LLM provider available" in str(e):
            raise QueryError(
                "No LLM provider available for query processing. "
                "To use OpenAI, set the OPENAI_API_KEY environment variable. "
                "To use Ollama, install it from https://ollama.ai/download and start it with 'ollama serve'. "
                "Then run 'ollama pull qwen3:4b' to download the default model."
            )
        elif "Database path not available" in str(e):
            raise QueryError(
                "Database path not available. Make sure the knowledge graph has been built "
                "using the 'build' method before querying. You can check if the graph is valid "
                "using the 'is_graph_valid()' method."
            )
        elif "No seed nodes found" in str(e) or "No relevant nodes found" in str(e):
            raise QueryError(
                "No relevant information found in the knowledge graph for this query. "
                "This could be because the information doesn't exist in the graph, or "
                "because the query terms don't match the available content. Try rephrasing "
                "your query or building a more comprehensive knowledge graph."
            )
        else:
            raise QueryError(f"Failed to query knowledge graph: {e}")
