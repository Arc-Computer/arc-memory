"""Core auto-refresh functionality for Arc Memory.

This module provides the core functionality for automatically refreshing the knowledge graph
with the latest data from various sources.
"""

import os
import time
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

from arc_memory.db import get_adapter
from arc_memory.db.metadata import (
    get_refresh_timestamp,
    get_all_refresh_timestamps,
)
from arc_memory.errors import AutoRefreshError
from arc_memory.ingest.adr import ADRIngestor
from arc_memory.ingest.change_patterns import ChangePatternIngestor
from arc_memory.ingest.code_analysis import CodeAnalysisIngestor
from arc_memory.ingest.git import GitIngestor
from arc_memory.ingest.github import GitHubIngestor
from arc_memory.ingest.linear import LinearIngestor
from arc_memory.llm.ollama_client import OllamaClient, ensure_ollama_available
from arc_memory.logging_conf import get_logger
from arc_memory.plugins import get_ingestor_plugins
from arc_memory.process.kgot import enhance_with_reasoning_structures
from arc_memory.process.semantic_analysis import enhance_with_semantic_analysis
from arc_memory.process.temporal_analysis import enhance_with_temporal_analysis
from arc_memory.schema.models import Edge, Node
from arc_memory.sql.db import add_nodes_and_edges, compress_db, ensure_arc_dir, ensure_path, get_db_path, init_db

# Import OpenAI client conditionally to avoid hard dependency
try:
    from arc_memory.llm.openai_client import OpenAIClient, ensure_openai_available
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import architecture extraction
from arc_memory.process.architecture_extraction import extract_architecture

logger = get_logger(__name__)


def get_ingestor_metadata(ingestor_name, db_path, verbose=False):
    """Get the last processed metadata for an ingestor.

    This function handles running the migration to ensure the metadata column exists,
    and then retrieves the last processed metadata for the specified ingestor.

    Args:
        ingestor_name: The name of the ingestor.
        db_path: Path to the database file.
        verbose: Whether to print verbose output.

    Returns:
        The last processed metadata for the ingestor, or None if not found.
    """
    from arc_memory.sql.db import get_connection

    # Run the migration to ensure the metadata column exists
    try:
        from arc_memory.migrations.add_metadata_column import run_migration
        run_migration(Path(db_path))
    except Exception as e:
        if verbose:
            print(f"  Warning: Failed to run migration: {e}")

    # Check if the database exists and get the last processed metadata
    db_conn = None
    last_processed = None
    try:
        db_conn = get_connection(Path(db_path), check_exists=True)

        # Try to get the last processed metadata for this ingestor
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT metadata FROM refresh_timestamps WHERE source = ?",
            (ingestor_name,)
        )
        result = cursor.fetchone()

        if result and result[0]:
            import json
            last_processed = json.loads(result[0])
            if verbose:
                print(f"  Found last processed metadata for {ingestor_name}")
    except Exception as e:
        if verbose:
            print(f"  No last processed metadata found for {ingestor_name}: {e}")
        last_processed = None
    finally:
        if db_conn:
            db_conn.close()

    return last_processed


def save_ingestor_metadata(ingestor_name, metadata, db_path, verbose=False):
    """Save metadata for an ingestor for future incremental updates.

    Args:
        ingestor_name: The name of the ingestor.
        metadata: The metadata to save.
        db_path: Path to the database file.
        verbose: Whether to print verbose output.

    Returns:
        True if successful, False otherwise.
    """
    if not metadata:
        return False

    from arc_memory.sql.db import get_connection

    try:
        # Connect to the database
        db_conn = get_connection(Path(db_path), check_exists=False)

        # Create the refresh_timestamps table if it doesn't exist
        cursor = db_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refresh_timestamps (
                source TEXT PRIMARY KEY,
                timestamp TEXT,
                metadata TEXT
            )
        """)

        # Save the metadata
        import json
        cursor.execute(
            "INSERT OR REPLACE INTO refresh_timestamps (source, timestamp, metadata) VALUES (?, ?, ?)",
            (ingestor_name, datetime.now().isoformat(), json.dumps(metadata))
        )
        db_conn.commit()
        db_conn.close()

        if verbose:
            print(f"  Saved metadata for {ingestor_name} for future incremental updates")
        return True
    except Exception as e:
        if verbose:
            print(f"  Failed to save metadata for {ingestor_name}: {e}")
        return False


def check_refresh_needed(
    source: str,
    min_interval: Optional[timedelta] = None,
    adapter_type: Optional[str] = None
) -> Tuple[bool, Optional[datetime]]:
    """Check if a source needs refreshing.

    Args:
        source: The source name (e.g., 'github', 'linear').
        min_interval: The minimum interval between refreshes. If None, defaults to 1 hour.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        A tuple of (needs_refresh, last_refresh_time), where needs_refresh is a boolean
        indicating whether the source needs refreshing, and last_refresh_time is the
        timestamp of the last refresh, or None if the source has never been refreshed.

    Raises:
        AutoRefreshError: If checking refresh status fails.
    """
    if min_interval is None:
        min_interval = timedelta(hours=1)

    try:
        last_refresh = get_refresh_timestamp(source, adapter_type)

        if last_refresh is None:
            # Source has never been refreshed
            logger.info(f"Source '{source}' has never been refreshed, refresh needed")
            return True, None

        now = datetime.now()
        time_since_refresh = now - last_refresh

        needs_refresh = time_since_refresh >= min_interval

        if needs_refresh:
            logger.info(
                f"Source '{source}' needs refreshing "
                f"(last refresh: {last_refresh.isoformat()}, "
                f"interval: {time_since_refresh})"
            )
        else:
            logger.debug(
                f"Source '{source}' does not need refreshing "
                f"(last refresh: {last_refresh.isoformat()}, "
                f"interval: {time_since_refresh})"
            )

        return needs_refresh, last_refresh
    except Exception as e:
        error_msg = f"Failed to check refresh status for source '{source}': {e}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "source": source,
                "min_interval": str(min_interval),
                "error": str(e),
            }
        )


def get_sources_needing_refresh(
    sources: Optional[List[str]] = None,
    min_interval: Optional[timedelta] = None,
    adapter_type: Optional[str] = None
) -> Dict[str, Optional[datetime]]:
    """Get a list of sources that need refreshing.

    Args:
        sources: A list of source names to check. If None, checks all known sources.
        min_interval: The minimum interval between refreshes. If None, defaults to 1 hour.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        A dictionary mapping source names to their last refresh timestamps (or None if never refreshed)
        for sources that need refreshing.

    Raises:
        AutoRefreshError: If checking refresh status fails.
    """
    if min_interval is None:
        min_interval = timedelta(hours=1)

    try:
        # If no sources specified, check all known sources
        if sources is None:
            # Get all sources that have been refreshed before
            all_timestamps = get_all_refresh_timestamps(adapter_type)
            sources = list(all_timestamps.keys())

            # Add default sources if they're not already in the list
            default_sources = ["github", "linear", "adr"]
            for source in default_sources:
                if source not in sources:
                    sources.append(source)

        sources_to_refresh = {}
        for source in sources:
            needs_refresh, last_refresh = check_refresh_needed(source, min_interval, adapter_type)
            if needs_refresh:
                sources_to_refresh[source] = last_refresh

        return sources_to_refresh
    except Exception as e:
        error_msg = f"Failed to get sources needing refresh: {e}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "sources": sources,
                "min_interval": str(min_interval),
                "error": str(e),
            }
        )


def refresh_source(
    source: str,
    force: bool = False,
    min_interval: Optional[timedelta] = None,
    adapter_type: Optional[str] = None
) -> bool:
    """Refresh a specific source.

    Args:
        source: The source name (e.g., 'github', 'linear').
        force: Whether to force a refresh even if the minimum interval hasn't elapsed.
        min_interval: The minimum interval between refreshes. If None, defaults to 1 hour.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        True if the source was refreshed, False otherwise.

    Raises:
        AutoRefreshError: If refreshing the source fails.
    """
    # Get the database adapter
    adapter = get_adapter(adapter_type)
    if not adapter.is_connected():
        from arc_memory.sql.db import get_db_path
        db_path = get_db_path()
        adapter.connect({"db_path": str(db_path)})
        adapter.init_db()

    try:
        # Check if refresh is needed
        if not force:
            needs_refresh, last_refresh = check_refresh_needed(source, min_interval, adapter_type)
            if not needs_refresh:
                logger.info(f"Skipping refresh for source '{source}' (last refresh: {last_refresh.isoformat() if last_refresh else 'never'})")
                return False

        # Import the source-specific refresh module dynamically
        import importlib
        try:
            module_name = f"arc_memory.auto_refresh.sources.{source}"
            module = importlib.import_module(module_name)
            refresh_func = getattr(module, "refresh")
        except (ImportError, AttributeError) as e:
            error_msg = f"Source '{source}' is not supported for auto-refresh: {e}"
            logger.error(error_msg)
            # Raise the exception to prevent further execution
            raise AutoRefreshError(
                error_msg,
                details={
                    "source": source,
                    "error": str(e),
                }
            )

        # Call the source-specific refresh function with the adapter
        logger.info(f"Refreshing source '{source}'")
        refresh_func(adapter)

        # Update the refresh timestamp directly using the adapter
        now = datetime.now()
        try:
            adapter.save_refresh_timestamp(source, now)
            logger.info(f"Successfully refreshed source '{source}' at {now.isoformat()}")
        except Exception as e:
            error_msg = f"Failed to save refresh timestamp for {source}: {e}"
            logger.error(error_msg)
            raise AutoRefreshError(
                error_msg,
                details={
                    "source": source,
                    "timestamp": now.isoformat(),
                    "error": str(e),
                }
            )

        return True
    except Exception as e:
        error_msg = f"Failed to refresh source '{source}': {e}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "source": source,
                "force": force,
                "min_interval": str(min_interval) if min_interval else None,
                "error": str(e),
            }
        )


def refresh_all_sources(
    sources: Optional[List[str]] = None,
    force: bool = False,
    min_interval: Optional[timedelta] = None,
    adapter_type: Optional[str] = None
) -> Dict[str, bool]:
    """Refresh all specified sources.

    Args:
        sources: A list of source names to refresh. If None, refreshes all known sources.
        force: Whether to force a refresh even if the minimum interval hasn't elapsed.
        min_interval: The minimum interval between refreshes. If None, defaults to 1 hour.
        adapter_type: The type of database adapter to use. If None, uses the configured adapter.

    Returns:
        A dictionary mapping source names to booleans indicating whether they were refreshed.

    Raises:
        AutoRefreshError: If refreshing any source fails.
    """
    if force:
        # If forcing refresh, use the provided sources or default ones
        sources_to_refresh = sources or ["github", "linear", "adr"]
    else:
        # Otherwise, get only the sources that need refreshing
        sources_needing_refresh = get_sources_needing_refresh(sources, min_interval, adapter_type)
        sources_to_refresh = list(sources_needing_refresh.keys())

    results = {}
    errors = []

    for source in sources_to_refresh:
        try:
            refreshed = refresh_source(source, force, min_interval, adapter_type)
            results[source] = refreshed
        except Exception as e:
            logger.error(f"Error refreshing source '{source}': {e}")
            results[source] = False
            errors.append((source, str(e)))

    if errors:
        error_details = {source: error for source, error in errors}
        error_msg = f"Failed to refresh {len(errors)} sources: {', '.join(source for source, _ in errors)}"
        logger.error(error_msg)
        raise AutoRefreshError(
            error_msg,
            details={
                "errors": error_details,
                "results": results,
            }
        )

    return results


class LLMEnhancementLevel:
    """LLM enhancement levels for the build process."""
    NONE = "none"
    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"


def refresh_knowledge_graph(
    repo_path: Union[str, Path],
    db_path: Optional[str] = None,
    include_github: bool = False,
    include_linear: bool = False,
    include_architecture: bool = True,
    use_llm: bool = True,
    llm_provider: str = "openai",
    llm_model: Optional[str] = "gpt-4.1",
    llm_enhancement_level: str = "standard",
    verbose: bool = False,
) -> Dict[str, Any]:
    """Refresh the knowledge graph with the latest data.

    This function builds or refreshes the knowledge graph from various sources,
    including Git, GitHub, Linear, and ADRs. It can also enhance the graph with
    LLM-derived insights.

    Args:
        repo_path: Path to the Git repository.
        db_path: Path to the database file. If None, uses the default path.
        include_github: Whether to include GitHub data.
        include_linear: Whether to include Linear data.
        use_llm: Whether to use LLM enhancement.
        llm_provider: The LLM provider to use ("ollama" or "openai").
        llm_model: The LLM model to use. If None, uses the default model for the provider.
        llm_enhancement_level: The level of LLM enhancement to apply ("none", "fast", "standard", "deep").
        verbose: Whether to print verbose output.

    Returns:
        A dictionary with the results of the refresh operation.
    """
    start_time = time.time()

    # Convert repo_path to Path if it's a string
    if isinstance(repo_path, str):
        repo_path = Path(repo_path)

    # Check if the repository exists
    if not repo_path.exists():
        raise AutoRefreshError(f"Repository path {repo_path} does not exist")

    # Resolve output path
    if db_path is None:
        arc_dir = ensure_arc_dir()
        db_path = str(arc_dir / "graph.db")

    if verbose:
        print(f"Repository: {repo_path}")
        print(f"Database: {db_path}")
        print(f"Include GitHub: {include_github}")
        print(f"Include Linear: {include_linear}")
        print(f"Use LLM: {use_llm}")
        if use_llm:
            print(f"LLM Provider: {llm_provider}")
            print(f"LLM Model: {llm_model or 'default'}")
            print(f"LLM Enhancement Level: {llm_enhancement_level}")

    # Set up ingestors
    ingestors = []

    # Create the Git ingestor
    git_ingestor = GitIngestor()
    ingestors.append(git_ingestor)

    # Create the GitHub ingestor if requested
    if include_github:
        github_ingestor = GitHubIngestor()
        ingestors.append(github_ingestor)

    # Create the Linear ingestor if requested
    if include_linear:
        linear_ingestor = LinearIngestor()
        ingestors.append(linear_ingestor)

    # Create the ADR ingestor
    adr_ingestor = ADRIngestor()
    ingestors.append(adr_ingestor)

    # Create the Change Pattern ingestor
    change_pattern_ingestor = ChangePatternIngestor()
    ingestors.append(change_pattern_ingestor)

    # Create the Code Analysis ingestor
    code_analysis_ingestor = CodeAnalysisIngestor()
    ingestors.append(code_analysis_ingestor)

    # Add plugin ingestors
    plugin_ingestors = get_ingestor_plugins()
    ingestors.extend(plugin_ingestors)

    # LLM setup if enhancement is enabled
    llm_client = None
    openai_client = None
    if use_llm:
        if verbose:
            print("Setting up LLM enhancement...")

        # Define system prompt for consistent reasoning
        system_prompt = """# Arc Memory Knowledge Graph Building Framework

## System Role
You are a specialized temporal knowledge graph enhancement system for Arc Memory. Your task is to analyze software repositories and enhance the knowledge graph with rich semantic, temporal, and reasoning structures.

## Arc Memory Schema
### Node Types:
- COMMIT: Git commits
- FILE: Repository files
- PR: Pull requests
- ISSUE: GitHub issues
- ADR: Architectural decision records
- FUNCTION: Code functions/methods
- CLASS: Code classes
- MODULE: Code modules
- COMPONENT: Architectural components
- SERVICE: System services
- DOCUMENT: Documentation files
- CONCEPT: Domain concepts
- REQUIREMENT: System requirements
- CHANGE_PATTERN: Patterns of changes over time
- REFACTORING: Code refactoring operations
- REASONING_QUESTION: Questions in reasoning structures
- REASONING_ALTERNATIVE: Alternatives in reasoning structures
- REASONING_CRITERION: Criteria in reasoning structures
- REASONING_STEP: Steps in reasoning processes
- REASONING_IMPLICATION: Implications of decisions

### Edge Types:
- MODIFIES: Commit modifies a file
- MERGES: PR merges a commit
- MENTIONS: PR/Issue mentions another entity
- DECIDES: ADR decides on a file/commit
- DEPENDS_ON: File/component depends on another
- CONTAINS: Module/Class contains a function
- CALLS: Function calls another function
- IMPORTS: Module imports another module
- INHERITS_FROM: Class inherits from another class
- IMPLEMENTS: Class implements an interface
- PART_OF: Component is part of a service
- DESCRIBES: Document describes a code entity
- REFERENCES: Document references another document
- FOLLOWS/PRECEDES: Temporal relationships
- CORRELATES_WITH: Changes correlate with each other
- REASONS_ABOUT: Reasoning about an entity
- HAS_ALTERNATIVE: Question has alternatives
- HAS_CRITERION: Question has criteria
- NEXT_STEP: Step leads to next step
- HAS_IMPLICATION: Decision has implications

## Framework Capabilities
1. **Code Structure Analysis**: Extract functions, classes, modules and their relationships
2. **Temporal Pattern Recognition**: Identify evolutionary patterns in development history
3. **Knowledge Graph of Thoughts**: Generate reasoning structures explaining design decisions
4. **Semantic Enhancement**: Infer implicit knowledge based on software engineering principles

## Expected Output Format
Generate structured JSON following the requested schema for each enhancement task. Include:
- Source provenance (commit ID, file path)
- Confidence scores (0.0-1.0) where appropriate
- Supporting evidence or rationale for inferences
"""

        # Set up the LLM client based on the provider
        if llm_provider == "openai":
            if not OPENAI_AVAILABLE:
                raise AutoRefreshError(
                    "OpenAI package not installed. Install with 'pip install openai'"
                )

            # Check if OpenAI API key is set
            if "OPENAI_API_KEY" not in os.environ:
                raise AutoRefreshError(
                    "OpenAI API key not set. Set the OPENAI_API_KEY environment variable."
                )

            # Set default model if not provided
            if llm_model is None:
                llm_model = "gpt-4.1"

            # Create OpenAI client
            try:
                openai_client = OpenAIClient()
                llm_client = openai_client  # Set llm_client to openai_client for compatibility
                if verbose:
                    print(f"✅ LLM setup complete with OpenAI model: {llm_model}")

                # Test the LLM with a simple query
                test_response = llm_client.generate(
                    model=llm_model,
                    prompt="Respond with a single word: Working",
                    system=system_prompt,
                    options={"temperature": 0.0}
                )

                if "working" in test_response.lower():
                    if verbose:
                        print("✅ LLM test query successful")
                else:
                    if verbose:
                        print(f"⚠️ LLM test query returned unexpected response: {test_response[:50]}...")
            except Exception as e:
                if verbose:
                    print(f"⚠️ Warning: LLM setup failed: {e}")
                use_llm = False
        else:  # Default to Ollama
            # Set default model if not provided
            if llm_model is None:
                llm_model = "qwen3:4b"

            # Check if Ollama is available
            if ensure_ollama_available(llm_model):
                llm_client = OllamaClient()
                if verbose:
                    print(f"✅ LLM setup complete with Ollama model: {llm_model}")

                # Test the LLM with a simple query
                try:
                    test_response = llm_client.generate(
                        model=llm_model,
                        prompt="Respond with a single word: Working",
                        system=system_prompt
                    )

                    if "working" in test_response.lower():
                        if verbose:
                            print("✅ LLM test query successful")
                    else:
                        if verbose:
                            print(f"⚠️ LLM test query returned unexpected response: {test_response[:50]}...")
                except Exception as e:
                    if verbose:
                        print(f"⚠️ Warning: LLM test query failed: {e}")
                    use_llm = False
            else:
                if verbose:
                    print("⚠️ Warning: Ollama not available, continuing without enhancement")
                use_llm = False

    # Process nodes and edges using ingestors
    all_nodes = []
    all_edges = []

    if verbose:
        print(f"Running {len(ingestors)} ingestors...")

    for idx, ingestor in enumerate(ingestors, 1):
        ingestor_name = ingestor.get_name()

        if verbose:
            print(f"[{idx}/{len(ingestors)}] Processing {ingestor_name}...")

        ingestor_start = time.time()

        try:
            # Get the last processed metadata for this ingestor
            last_processed = get_ingestor_metadata(ingestor_name, db_path, verbose)

            # Call the ingest method with the appropriate parameters for each ingestor type
            if ingestor_name == "git":
                nodes, edges, metadata = ingestor.ingest(
                    repo_path=repo_path,
                    last_processed=last_processed,  # Use last_processed for incremental builds
                )
            elif ingestor_name == "github":
                nodes, edges, metadata = ingestor.ingest(
                    repo_path=repo_path,
                    last_processed=last_processed,  # Use last_processed for incremental builds
                )
            elif ingestor_name == "adr":
                nodes, edges, metadata = ingestor.ingest(
                    repo_path=repo_path,
                    last_processed=last_processed,
                )
            elif ingestor_name == "code_analysis":
                nodes, edges, metadata = ingestor.ingest(
                    repo_path=repo_path,
                    last_processed=last_processed,
                    llm_enhancement_level=llm_enhancement_level if use_llm else "none",
                    ollama_client=llm_client if llm_provider == "ollama" and use_llm else None,
                )
            elif ingestor_name == "change_patterns":
                nodes, edges, metadata = ingestor.ingest(
                    repo_path=repo_path,
                    last_processed=last_processed,
                    llm_enhancement_level=llm_enhancement_level if use_llm else "none",
                    ollama_client=llm_client if llm_provider == "ollama" and use_llm else None,
                )
            else:
                # Default handling for other ingestors
                if hasattr(ingestor, "ingest") and "repo_path" in ingestor.ingest.__code__.co_varnames:
                    nodes, edges, metadata = ingestor.ingest(
                        repo_path=repo_path,
                        last_processed=last_processed,
                    )
                else:
                    nodes, edges, metadata = ingestor.ingest(
                        last_processed=last_processed,
                    )
        except Exception as e:
            if verbose:
                print(f"❌ Error processing {ingestor_name}: {e}")
            nodes, edges, metadata = [], [], {}

        ingestor_time = time.time() - ingestor_start
        all_nodes.extend(nodes)
        all_edges.extend(edges)

        # Save the metadata for this ingestor for future incremental updates
        save_ingestor_metadata(ingestor_name, metadata, db_path, verbose)

        if verbose:
            print(f"✅ [{idx}/{len(ingestors)}] {ingestor_name}: {len(nodes)} nodes, {len(edges)} edges ({ingestor_time:.1f}s)")

    # Extract architecture components if enabled
    if include_architecture:
        if verbose:
            print("Extracting architecture components...")

        arch_start = time.time()
        try:
            # Create a repository ID if we're using architecture
            import hashlib
            repo_id = f"repository:{hashlib.md5(str(repo_path.absolute()).encode()).hexdigest()}"

            # Extract architecture components
            arch_nodes, arch_edges = extract_architecture(all_nodes, all_edges, repo_path, repo_id)

            # Add architecture nodes and edges to the graph
            all_nodes.extend(arch_nodes)
            all_edges.extend(arch_edges)

            if verbose:
                print(f"✅ Architecture extraction complete: {len(arch_nodes)} nodes, {len(arch_edges)} edges ({time.time() - arch_start:.1f}s)")
        except Exception as e:
            if verbose:
                print(f"❌ Architecture extraction failed: {e}")

    # Apply LLM enhancements if enabled
    if use_llm and llm_client is not None:
        if verbose:
            print("Applying LLM enhancements...")

        enhancement_start = time.time()

        # Apply semantic analysis
        if verbose:
            print("Enhancing with semantic analysis...")

        try:
            all_nodes, all_edges = enhance_with_semantic_analysis(
                all_nodes,
                all_edges,
                repo_path=repo_path,
                enhancement_level=llm_enhancement_level,
                ollama_client=llm_client if llm_provider == "ollama" else None,
                openai_client=openai_client if llm_provider == "openai" else None,
                llm_provider=llm_provider,
            )
            if verbose:
                print(f"✅ Semantic analysis complete ({time.time() - enhancement_start:.1f}s)")
        except Exception as e:
            if verbose:
                print(f"❌ Semantic analysis failed: {e}")

        # Apply temporal analysis
        temporal_start = time.time()
        if verbose:
            print("Enhancing with temporal analysis...")

        try:
            all_nodes, all_edges = enhance_with_temporal_analysis(
                all_nodes,
                all_edges,
                repo_path=repo_path,
                enhancement_level=llm_enhancement_level,
                ollama_client=llm_client if llm_provider == "ollama" else None,
                openai_client=openai_client if llm_provider == "openai" else None,
                llm_provider=llm_provider,
            )
            if verbose:
                print(f"✅ Temporal analysis complete ({time.time() - temporal_start:.1f}s)")
        except Exception as e:
            if verbose:
                print(f"❌ Temporal analysis failed: {e}")

        # Apply KGoT reasoning structures (only in standard or deep mode)
        if llm_enhancement_level in ["standard", "deep"]:
            kgot_start = time.time()
            if verbose:
                print("Generating reasoning structures...")

            try:
                all_nodes, all_edges = enhance_with_reasoning_structures(
                    all_nodes,
                    all_edges,
                    repo_path=repo_path,
                    ollama_client=llm_client if llm_provider == "ollama" else None,
                    openai_client=openai_client if llm_provider == "openai" else None,
                    llm_provider=llm_provider,
                    enhancement_level=llm_enhancement_level,
                    system_prompt=system_prompt
                )
                if verbose:
                    print(f"✅ Reasoning structures complete ({time.time() - kgot_start:.1f}s)")
            except Exception as e:
                if verbose:
                    print(f"❌ Reasoning structures failed: {e}")

        enhancement_time = time.time() - enhancement_start
        if verbose:
            print(f"✅ LLM enhancements complete ({enhancement_time:.1f}s)")

    # Store the graph
    if verbose:
        print(f"Writing graph to database ({len(all_nodes)} nodes, {len(all_edges)} edges)...")

    # Initialize the database
    # The init_db function will handle string paths
    conn = init_db(db_path)

    # Add nodes and edges
    add_nodes_and_edges(conn, all_nodes, all_edges)

    # Compress the database
    if verbose:
        print("Compressing database...")

    compressed_path = compress_db(db_path)

    # Get file sizes for reporting
    original_size = os.path.getsize(db_path)
    compressed_size = os.path.getsize(compressed_path)
    compression_ratio = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0

    total_time = time.time() - start_time

    if verbose:
        print(f"Build complete in {total_time:.1f} seconds!")
        print(f"{len(all_nodes)} nodes and {len(all_edges)} edges")
        print(f"Database saved to {db_path} and compressed to {compressed_path}")
        print(f"({original_size/1024/1024:.1f} MB → {compressed_size/1024/1024:.1f} MB, {compression_ratio:.1f}% reduction)")

    return {
        "nodes_added": len(all_nodes),
        "edges_added": len(all_edges),
        "nodes_updated": 0,  # Not tracked in this implementation
        "edges_updated": 0,  # Not tracked in this implementation
        "build_time": total_time,
        "db_path": db_path,
        "compressed_path": compressed_path,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "compression_ratio": compression_ratio,
    }
