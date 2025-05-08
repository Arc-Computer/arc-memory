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
    token: Optional[str] = typer.Option(
        None, "--token", "-t", help="GitHub Personal Access Token."
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
        arc build --token <github-token>

        # Build with Linear data
        arc build --linear

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
        ingestors.append(
            GitIngestor(
                repo_path=repo_path,
                max_commits=max_commits,
                days=days,
                incremental=incremental,
                pull=pull,
            )
        )

        # Create the GitHub ingestor if a token is provided
        if token:
            ingestors.append(
                GitHubIngestor(
                    repo_path=repo_path,
                    token=token,
                    incremental=incremental,
                )
            )

        # Create the Linear ingestor if requested
        if linear:
            ingestors.append(LinearIngestor(incremental=incremental))

        # Create the ADR ingestor
        ingestors.append(ADRIngestor(repo_path=repo_path))
        
        # Create the Change Pattern ingestor
        ingestors.append(ChangePatternIngestor())
        
        # Create the Code Analysis ingestor
        ingestors.append(CodeAnalysisIngestor(repo_path=repo_path))

        # Add plugin ingestors
        plugin_ingestors = get_ingestor_plugins(repo_path=repo_path)
        ingestors.extend(plugin_ingestors)
        
        # LLM setup if enhancement is enabled
        ollama_client = None
        if llm_enhancement != LLMEnhancementLevel.NONE:
            print("🔄 Setting up LLM enhancement...")
            if ensure_ollama_available("qwen3:4b"):
                ollama_client = OllamaClient(host=ollama_host)
                print("✅ LLM setup complete")
            else:
                print("⚠️  Warning: LLM setup failed, continuing without enhancement")
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
            nodes, edges, metadata = ingestor.ingest(
                previous_nodes=all_nodes,
                previous_edges=all_edges,
                llm_enhancement_level=llm_enhancement.value,
                ollama_client=ollama_client,
            )
            
            ingestor_time = time.time() - ingestor_start
            all_nodes.extend(nodes)
            all_edges.extend(edges)
            
            # Print completion status with stats
            sys.stdout.write(f"\r{' ' * 80}\r")
            sys.stdout.write(f"✅ [{idx}/{total_ingestors}] {ingestor_name}: {len(nodes)} nodes, {len(edges)} edges ({ingestor_time:.1f}s)\n")
            sys.stdout.flush()

        # Apply LLM enhancements if enabled
        if llm_enhancement != LLMEnhancementLevel.NONE:
            print("\n🧠 Applying LLM enhancements...")
            enhancement_start = time.time()
            
            # Apply semantic analysis
            spinner_idx = 0
            semantic_spinner_thread = None
            sys.stdout.write("\r⠋ Enhancing with semantic analysis...")
            sys.stdout.flush()
            
            try:
                all_nodes, all_edges = enhance_with_semantic_analysis(
                    all_nodes, all_edges, ollama_client=ollama_client
                )
                sys.stdout.write(f"\r✅ Semantic analysis complete ({time.time() - enhancement_start:.1f}s)\n")
            except Exception as e:
                sys.stdout.write(f"\r❌ Semantic analysis failed: {e}\n")
            
            # Apply temporal analysis
            temporal_start = time.time()
            sys.stdout.write("\r⠋ Enhancing with temporal analysis...")
            sys.stdout.flush()
            
            try:
                all_nodes, all_edges = enhance_with_temporal_analysis(
                    all_nodes, all_edges
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
                    all_nodes, all_edges = enhance_with_reasoning_structures(
                        all_nodes, all_edges, repo_path=repo_path
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
        original_size, compressed_size = compress_db(output_path)
        compression_ratio = (original_size - compressed_size) / original_size * 100
        
        total_time = time.time() - start_time
        print(f"\n✨ Build complete in {total_time:.1f} seconds!")
        print(f"📊 {len(all_nodes)} nodes and {len(all_edges)} edges")
        print(f"💾 Database saved to {output_path} and compressed to {output_path}.zst")
        print(f"   ({original_size/1024/1024:.1f} MB → {compressed_size/1024/1024:.1f} MB, {compression_ratio:.1f}% reduction)")
        
    except Exception as e:
        raise GraphBuildError(f"Error building graph: {e}")
