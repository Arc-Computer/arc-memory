"""Build command for Arc Memory.

This module implements the build command, which builds a knowledge graph
from a Git repository and optionally ingests data from other sources.
"""

import enum
import os
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import typer

from arc_memory.errors import GraphBuildError
from arc_memory.ingest.adr import ADRIngestor
from arc_memory.ingest.change_patterns import ChangePatternIngestor
from arc_memory.ingest.code_analysis import CodeAnalysisIngestor
from arc_memory.ingest.git import GitIngestor
from arc_memory.ingest.github import GitHubIngestor
from arc_memory.ingest.linear import LinearIngestor
from arc_memory.llm.ollama_client import OllamaClient, ensure_ollama_available
from arc_memory.logging_conf import get_logger

# Import OpenAI client conditionally to avoid hard dependency
try:
    from arc_memory.llm.openai_client import OpenAIClient, ensure_openai_available
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
from arc_memory.plugins import get_ingestor_plugins
from arc_memory.process.kgot import enhance_with_reasoning_structures
from arc_memory.process.semantic_analysis import enhance_with_semantic_analysis
from arc_memory.process.temporal_analysis import enhance_with_temporal_analysis
from arc_memory.schema.models import Edge, Node
from arc_memory.sql.db import add_nodes_and_edges, compress_db, ensure_arc_dir, init_db

app = typer.Typer(help="Build a knowledge graph from various sources.")
logger = get_logger(__name__)


class LLMEnhancementLevel(str, Enum):
    """LLM enhancement levels for the build process."""

    NONE = "none"
    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"


def build(
    repo_path: Path = typer.Option(
        Path.cwd(), "--repo", "-r", help="Path to the Git repository."
    ),
    output_path: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Path to the output database file."
    ),
    max_commits: int = typer.Option(
        5000, "--max-commits", help="Maximum number of commits to process."
    ),
    days: int = typer.Option(
        365, "--days", help="Maximum age of commits to process in days."
    ),
    incremental: bool = typer.Option(
        False, "--incremental", help="Only process new data since last build."
    ),
    pull: bool = typer.Option(
        False, "--pull", help="Pull the latest changes from the remote repository."
    ),
    github: bool = typer.Option(
        False, "--github", help="Fetch data from GitHub."
    ),
    token: Optional[str] = typer.Option(
        None, "--token", "-t", help="GitHub Personal Access Token (deprecated, use --github instead)."
    ),
    linear: bool = typer.Option(
        False, "--linear", help="Fetch data from Linear."
    ),
    llm_enhancement: LLMEnhancementLevel = typer.Option(
        LLMEnhancementLevel.NONE,
        "--llm-enhancement",
        "-l",
        help="LLM enhancement level: none, fast, standard, deep.",
    ),
    llm_provider: str = typer.Option(
        "ollama",
        "--llm-provider",
        help="LLM provider to use: ollama or openai.",
    ),
    llm_model: Optional[str] = typer.Option(
        None,
        "--llm-model",
        help="LLM model to use (defaults to qwen3:4b for Ollama, gpt-3.5-turbo for OpenAI).",
    ),
    ollama_host: str = typer.Option(
        "http://localhost:11434",
        "--ollama-host",
        help="Ollama API host URL.",
    ),
    ci_mode: bool = typer.Option(
        False, "--ci-mode", help="Run in CI mode with optimized parameters."
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
) -> None:
    """Build the knowledge graph from a Git repository and other sources.

    This command builds a knowledge graph from a Git repository and optionally
    ingests data from other sources like GitHub and Linear. The resulting graph
    is stored in a SQLite database.

    Examples:
        # Build from the current directory
        arc build

        # Build from a specific repository
        arc build --repo /path/to/repo

        # Build with a specific output file
        arc build --output /path/to/output.db

        # Build with GitHub data
        arc build --github

        # Build with Linear data
        arc build --linear

        # Build with both GitHub and Linear data
        arc build --github --linear

        # Build with LLM enhancement
        arc build --llm-enhancement standard
    """
    try:
        start_time = time.time()

        # Print welcome message
        print("\n📊 Arc Memory Knowledge Graph Builder")
        print("=====================================")
        print(f"Repository: {repo_path}")
        print(f"Max commits: {max_commits}")
        print(f"Days: {days}")
        if incremental:
            print("Mode: Incremental (only processing new data)")
        else:
            print("Mode: Full rebuild")

        print(f"LLM Enhancement: {llm_enhancement.value}")
        if llm_enhancement != LLMEnhancementLevel.NONE:
            print(f"Ollama Host: {ollama_host}")
        print()

        # Check if the repository exists
        if not repo_path.exists():
            raise GraphBuildError(f"Repository path {repo_path} does not exist")

        # Resolve output path
        if output_path is None:
            arc_dir = ensure_arc_dir()
            output_path = arc_dir / "graph.db"

        # Set up ingestors
        ingestors = []

        # Create the Git ingestor
        git_ingestor = GitIngestor()
        ingestors.append(git_ingestor)

        # Create the GitHub ingestor if requested or if a token is provided
        if github or token:
            github_ingestor = GitHubIngestor()
            ingestors.append(github_ingestor)

        # Create the Linear ingestor if requested
        if linear:
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
        ollama_client = None
        openai_client = None
        if llm_enhancement != LLMEnhancementLevel.NONE:
            print("🔄 Setting up LLM enhancement...")
            print(f"LLM Provider: {llm_provider}")
            if llm_model:
                print(f"LLM Model: {llm_model}")

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

## Few-Shot Examples

### Example 1: Temporal Pattern Analysis
```json
{
  "pattern_type": "code_evolution",
  "description": "Authentication module refactoring sequence",
  "confidence": 0.92,
  "temporal_nodes": [
    {
      "id": "commit:a1b2c3",
      "type": "commit",
      "properties": {
        "message": "Initial auth implementation",
        "author": "developer@example.com"
      }
    },
    {
      "id": "commit:d4e5f6",
      "type": "commit",
      "properties": {
        "message": "Refactor auth flow for better security",
        "author": "security@example.com"
      }
    }
  ],
  "temporal_edges": [
    {
      "src": "commit:a1b2c3",
      "dst": "commit:d4e5f6",
      "rel": "PRECEDES",
      "properties": {
        "context": "Security improvement",
        "files_affected": ["auth/login.py", "auth/session.py"]
      }
    }
  ],
  "rationale": "The commit sequence shows a deliberate evolution of the authentication system with security improvements added after initial implementation."
}
```

### Example 2: Knowledge Graph of Thoughts (KGoT)
```json
{
  "question": "What authentication approach should we use?",
  "alternatives": [
    {
      "name": "JWT-based authentication",
      "description": "Using JSON Web Tokens for stateless authentication"
    },
    {
      "name": "Session-based authentication",
      "description": "Using server-side sessions with cookies"
    }
  ],
  "criteria": [
    {
      "name": "Scalability",
      "description": "How well the solution scales with increased users"
    },
    {
      "name": "Security",
      "description": "Protection against common authentication attacks"
    }
  ],
  "reasoning": [
    {
      "step": 1,
      "description": "Identified need for stateless authentication due to microservice architecture"
    },
    {
      "step": 2,
      "description": "Evaluated JWT vs. session-based approaches for scalability and security"
    },
    {
      "step": 3,
      "description": "Selected JWT as optimal solution based on scalability requirements"
    }
  ],
  "implications": [
    "Need to implement proper token expiration and refresh mechanism",
    "Must secure signing keys and rotate them periodically"
  ]
}
```

### Example 3: Code Relationship Enhancement
```json
{
  "enhancement_type": "code_relationships",
  "module_id": "module:src/auth/index.ts",
  "inferred_relationships": [
    {
      "relationship": "CALLS",
      "source": "function:src/auth/login.ts:authenticateUser",
      "target": "function:src/auth/token.ts:generateToken",
      "confidence": 0.94,
      "evidence": "Function call at line 42 in login.ts"
    },
    {
      "relationship": "DEPENDS_ON",
      "source": "module:src/auth/session.ts",
      "target": "module:src/database/index.ts",
      "confidence": 0.87,
      "evidence": "Import statement and function calls accessing database entities"
    }
  ],
  "component_inference": {
    "component_name": "Authentication Service",
    "confidence": 0.91,
    "modules": [
      "module:src/auth/index.ts",
      "module:src/auth/login.ts",
      "module:src/auth/token.ts"
    ],
    "rationale": "These modules collectively implement authentication functionality with clear boundaries"
  }
}
```

Prioritize precision over coverage in your enhancements. Follow Arc Memory's schema exactly to ensure all nodes and relationships integrate cleanly with the existing knowledge graph.
"""

            # Set up the LLM client based on the provider
            if llm_provider == "openai":
                if not OPENAI_AVAILABLE:
                    print("⚠️ OpenAI package not installed. Install with 'pip install openai'")
                    print("⚠️ Falling back to Ollama")
                    llm_provider = "ollama"
                else:
                    # Check if OpenAI API key is set
                    if "OPENAI_API_KEY" not in os.environ:
                        print("⚠️ OpenAI API key not set. Set the OPENAI_API_KEY environment variable.")
                        print("⚠️ Falling back to Ollama")
                        llm_provider = "ollama"
                    else:
                        # Set default model if not provided
                        openai_model = llm_model or "gpt-4.1"

                        # Create OpenAI client
                        try:
                            openai_client = OpenAIClient()
                            print(f"✅ LLM setup complete with OpenAI model: {openai_model}")

                            # Test the LLM with a simple query
                            test_response = openai_client.generate(
                                model=openai_model,
                                prompt="Respond with a single word: Working",
                                system=system_prompt,
                                options={"temperature": 0.0}
                            )

                            if "working" in test_response.lower():
                                print("✅ LLM test query successful")
                            else:
                                print(f"⚠️ LLM test query returned unexpected response: {test_response[:50]}...")
                        except Exception as e:
                            print(f"⚠️ Warning: OpenAI setup failed: {e}")
                            print("⚠️ Falling back to Ollama")
                            llm_provider = "ollama"

            # If using Ollama (either by choice or as fallback)
            if llm_provider == "ollama":
                # Set default model if not provided
                ollama_model = llm_model or "qwen3:4b"

                # Check if Ollama is available
                if ensure_ollama_available(ollama_model):
                    ollama_client = OllamaClient(host=ollama_host)
                    print(f"✅ LLM setup complete with Ollama model: {ollama_model}")

                    # Test the LLM with a simple query
                    try:
                        test_response = ollama_client.generate(
                            model=ollama_model,
                            prompt="Respond with a single word: Working",
                            system=system_prompt
                        )

                        if "working" in test_response.lower():
                            print("✅ LLM test query successful")
                        else:
                            print(f"⚠️ LLM test query returned unexpected response: {test_response[:50]}...")
                    except Exception as e:
                        print(f"⚠️ Warning: Ollama test query failed: {e}")
                        llm_enhancement = LLMEnhancementLevel.NONE
                else:
                    print("⚠️ Warning: Ollama not available, continuing without enhancement")
                    llm_enhancement = LLMEnhancementLevel.NONE

            # If neither provider is available, disable enhancement
            if llm_provider not in ["openai", "ollama"]:
                print(f"⚠️ Unsupported LLM provider: {llm_provider}")
                print("⚠️ Supported providers: openai, ollama")
                llm_enhancement = LLMEnhancementLevel.NONE

        # Process nodes and edges using ingestors
        all_nodes = []
        all_edges = []

        total_ingestors = len(ingestors)
        print(f"\n🔍 Running {total_ingestors} ingestors...\n")

        # Define a spinner animation for progress
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner_idx = 0

        for idx, ingestor in enumerate(ingestors, 1):
            ingestor_name = ingestor.get_name()

            # Clear current line and print status
            sys.stdout.write(f"\r{' ' * 80}\r")
            sys.stdout.write(f"[{idx}/{total_ingestors}] Processing {ingestor_name}...")
            sys.stdout.flush()

            ingestor_start = time.time()

            try:
                # Call the ingest method with the appropriate parameters for each ingestor type
                if ingestor_name == "git":
                    nodes, edges, metadata = ingestor.ingest(
                        repo_path=repo_path,
                        max_commits=max_commits,
                        days=days,
                        last_processed=None,  # Use None for full builds or populate for incremental
                    )
                elif ingestor_name == "github":
                    nodes, edges, metadata = ingestor.ingest(
                        repo_path=repo_path,
                        token=token,
                        last_processed=None,  # Use None for full builds or populate for incremental
                    )
                elif ingestor_name == "adr":
                    nodes, edges, metadata = ingestor.ingest(
                        repo_path=repo_path,
                        last_processed=None,
                    )
                elif ingestor_name == "code_analysis":
                    nodes, edges, metadata = ingestor.ingest(
                        repo_path=repo_path,
                        last_processed=None,
                        llm_enhancement_level=llm_enhancement.value,
                    )
                elif ingestor_name == "change_patterns":
                    nodes, edges, metadata = ingestor.ingest(
                        repo_path=repo_path,
                        last_processed=None,
                        llm_enhancement_level=llm_enhancement.value,
                    )
                else:
                    # Default handling for other ingestors - handle the case where repo_path might be needed
                    if hasattr(ingestor, "ingest") and "repo_path" in ingestor.ingest.__code__.co_varnames:
                        nodes, edges, metadata = ingestor.ingest(
                            repo_path=repo_path,
                            last_processed=None,
                        )
                    else:
                        nodes, edges, metadata = ingestor.ingest(
                            last_processed=None,
                        )
            except Exception as e:
                print(f"\r❌ Error processing {ingestor_name}: {e}")
                nodes, edges, metadata = [], [], {}

            ingestor_time = time.time() - ingestor_start
            all_nodes.extend(nodes)
            all_edges.extend(edges)

            # Print completion status with stats
            sys.stdout.write(f"\r{' ' * 80}\r")
            sys.stdout.write(f"✅ [{idx}/{total_ingestors}] {ingestor_name}: {len(nodes)} nodes, {len(edges)} edges ({ingestor_time:.1f}s)\n")
            sys.stdout.flush()

        # Apply LLM enhancements if enabled
        if llm_enhancement != LLMEnhancementLevel.NONE and (ollama_client is not None or openai_client is not None):
            print("\n🧠 Applying LLM enhancements...")
            enhancement_start = time.time()

            # Apply semantic analysis
            spinner_idx = 0
            sys.stdout.write("\r⠋ Enhancing with semantic analysis...")
            sys.stdout.flush()

            try:
                if llm_provider == "openai" and openai_client is not None:
                    all_nodes, all_edges = enhance_with_semantic_analysis(
                        all_nodes,
                        all_edges,
                        repo_path=repo_path,
                        enhancement_level=llm_enhancement.value,
                        openai_client=openai_client,
                        llm_provider="openai"
                    )
                else:
                    all_nodes, all_edges = enhance_with_semantic_analysis(
                        all_nodes,
                        all_edges,
                        repo_path=repo_path,
                        enhancement_level=llm_enhancement.value,
                        ollama_client=ollama_client,
                        llm_provider="ollama"
                    )
                sys.stdout.write(f"\r✅ Semantic analysis complete ({time.time() - enhancement_start:.1f}s)\n")
            except Exception as e:
                sys.stdout.write(f"\r❌ Semantic analysis failed: {e}\n")

            # Apply temporal analysis
            temporal_start = time.time()
            sys.stdout.write("\r⠋ Enhancing with temporal analysis...")
            sys.stdout.flush()

            try:
                if llm_provider == "openai" and openai_client is not None:
                    all_nodes, all_edges = enhance_with_temporal_analysis(
                        all_nodes,
                        all_edges,
                        repo_path=repo_path,
                        enhancement_level=llm_enhancement.value,
                        openai_client=openai_client,
                        llm_provider="openai"
                    )
                else:
                    all_nodes, all_edges = enhance_with_temporal_analysis(
                        all_nodes,
                        all_edges,
                        repo_path=repo_path,
                        enhancement_level=llm_enhancement.value,
                        ollama_client=ollama_client,
                        llm_provider="ollama"
                    )
                sys.stdout.write(f"\r✅ Temporal analysis complete ({time.time() - temporal_start:.1f}s)\n")
            except Exception as e:
                sys.stdout.write(f"\r❌ Temporal analysis failed: {e}\n")

            # Apply KGoT reasoning structures (only in standard or deep mode)
            if llm_enhancement in [LLMEnhancementLevel.STANDARD, LLMEnhancementLevel.DEEP]:
                kgot_start = time.time()
                sys.stdout.write("\r⠋ Generating reasoning structures...")
                sys.stdout.flush()

                try:
                    if llm_provider == "openai" and openai_client is not None:
                        all_nodes, all_edges = enhance_with_reasoning_structures(
                            all_nodes,
                            all_edges,
                            repo_path=repo_path,
                            openai_client=openai_client,
                            llm_provider="openai",
                            enhancement_level=llm_enhancement.value,
                            system_prompt=system_prompt
                        )
                    else:
                        all_nodes, all_edges = enhance_with_reasoning_structures(
                            all_nodes,
                            all_edges,
                            repo_path=repo_path,
                            ollama_client=ollama_client,
                            llm_provider="ollama",
                            enhancement_level=llm_enhancement.value,
                            system_prompt=system_prompt
                        )
                    sys.stdout.write(f"\r✅ Reasoning structures complete ({time.time() - kgot_start:.1f}s)\n")
                except Exception as e:
                    sys.stdout.write(f"\r❌ Reasoning structures failed: {e}\n")

            enhancement_time = time.time() - enhancement_start
            print(f"✅ LLM enhancements complete ({enhancement_time:.1f}s)")

        # Store the graph
        print(f"\n💾 Writing graph to database ({len(all_nodes)} nodes, {len(all_edges)} edges)...")
        db_start = time.time()

        # Initialize the database
        conn = init_db(output_path)

        # Add nodes and edges
        add_nodes_and_edges(conn, all_nodes, all_edges)

        # Compress the database
        print("🗜️  Compressing database...")
        compressed_path = compress_db(output_path)

        # Get file sizes for reporting
        original_size = output_path.stat().st_size
        compressed_size = compressed_path.stat().st_size
        compression_ratio = (original_size - compressed_size) / original_size * 100

        total_time = time.time() - start_time
        print(f"\n✨ Build complete in {total_time:.1f} seconds!")
        print(f"📊 {len(all_nodes)} nodes and {len(all_edges)} edges")
        print(f"💾 Database saved to {output_path} and compressed to {compressed_path}")
        print(f"   ({original_size/1024/1024:.1f} MB → {compressed_size/1024/1024:.1f} MB, {compression_ratio:.1f}% reduction)")

    except Exception as e:
        raise GraphBuildError(f"Error building graph: {e}")
