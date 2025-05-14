#!/usr/bin/env python3
"""
Benchmark script for incremental knowledge graph building.

This script benchmarks the performance of incremental builds vs. full builds:
1. First checking if a graph exists
2. If it exists, performing an incremental update and measuring the time
3. If it doesn't exist, performing a full build and measuring the time
4. Optionally forcing a full build for comparison

Usage:
    python test_incremental_build.py [--force-full]

Options:
    --force-full    Force a full build even if a graph exists, for benchmarking
"""

import os
import time
import sys
import json
from pathlib import Path
from datetime import datetime

from arc_memory.sdk import Arc
from arc_memory.auto_refresh.core import refresh_knowledge_graph
from arc_memory.sql.db import get_connection, get_db_path

def check_graph_exists(db_path):
    """Check if a graph exists at the given path."""
    try:
        conn = get_connection(Path(db_path), check_exists=True)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes")
        node_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM edges")
        edge_count = cursor.fetchone()[0]
        conn.close()
        return True, node_count, edge_count
    except Exception as e:
        print(f"No existing graph found: {e}")
        return False, 0, 0

def check_refresh_timestamps(db_path):
    """Check if refresh timestamps exist in the database."""
    try:
        conn = get_connection(Path(db_path), check_exists=True)
        cursor = conn.cursor()

        # Check if the refresh_timestamps table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='refresh_timestamps'")
        if not cursor.fetchone():
            print("refresh_timestamps table does not exist")
            conn.close()
            return False, []

        # Get all refresh timestamps
        cursor.execute("SELECT source, timestamp, metadata FROM refresh_timestamps")
        timestamps = cursor.fetchall()
        conn.close()

        if not timestamps:
            print("No refresh timestamps found")
            return False, []

        print(f"Found {len(timestamps)} refresh timestamps:")
        for source, timestamp, metadata in timestamps:
            print(f"  {source}: {timestamp}")

        return True, timestamps
    except Exception as e:
        print(f"Error checking refresh timestamps: {e}")
        return False, []

def run_benchmark(force_full=False):
    """Run benchmark for incremental vs. full builds.

    Args:
        force_full: Whether to force a full build even if a graph exists.

    Returns:
        A dictionary with benchmark results.
    """
    # Get the repository path
    repo_path = os.path.abspath(".")
    print(f"Repository path: {repo_path}")

    # Get the default database path
    db_path = str(get_db_path())
    print(f"Database path: {db_path}")

    # Check if a graph exists
    graph_exists, node_count, edge_count = check_graph_exists(db_path)
    if graph_exists:
        print(f"Existing graph found with {node_count} nodes and {edge_count} edges")
    else:
        print("No existing graph found")

    # Check if refresh timestamps exist
    has_timestamps, timestamps = check_refresh_timestamps(db_path)
    if has_timestamps:
        print(f"Found {len(timestamps)} refresh timestamps")
    else:
        print("No refresh timestamps found")

    # Get OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: No OpenAI API key found in environment variables")
        print("Using Ollama for LLM enhancement")
        use_llm = False
        llm_provider = "ollama"
        llm_model = None
    else:
        print("Using OpenAI for LLM enhancement")
        use_llm = True
        llm_provider = "openai"
        llm_model = "gpt-4.1"

    benchmark_results = {
        "repository_path": repo_path,
        "database_path": db_path,
        "graph_exists": graph_exists,
        "node_count": node_count,
        "edge_count": edge_count,
        "has_timestamps": has_timestamps,
        "timestamp_count": len(timestamps) if has_timestamps else 0,
        "use_llm": use_llm,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
    }

    # Perform incremental update if graph exists and not forcing full build
    if graph_exists and not force_full:
        print("\nPerforming incremental update...")
        start_time = time.time()

        # Use the refresh_knowledge_graph function directly with "fast" enhancement level
        result = refresh_knowledge_graph(
            repo_path=repo_path,
            include_github=True,
            use_llm=use_llm,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_enhancement_level="fast",  # Use fast enhancement level for incremental updates
            verbose=True
        )

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"\nIncremental update completed in {elapsed_time:.2f} seconds")
        print(f"Added {result['nodes_added']} nodes and {result['edges_added']} edges")

        benchmark_results.update({
            "build_type": "incremental",
            "elapsed_time": elapsed_time,
            "nodes_added": result["nodes_added"],
            "edges_added": result["edges_added"],
        })
    else:
        # Perform full build if graph doesn't exist or forcing full build
        build_type = "forced_full" if force_full else "initial_full"
        print(f"\nPerforming {build_type} build...")
        start_time = time.time()

        # Initialize Arc
        arc = Arc(repo_path=repo_path)

        # Build the knowledge graph
        result = arc.build(
            include_github=True,
            use_llm=use_llm,
            llm_provider=llm_provider,
            llm_model=llm_model,
            verbose=True
        )

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"\n{build_type.capitalize()} build completed in {elapsed_time:.2f} seconds")
        print(f"Added {result['nodes_added']} nodes and {result['edges_added']} edges")

        benchmark_results.update({
            "build_type": build_type,
            "elapsed_time": elapsed_time,
            "nodes_added": result["nodes_added"],
            "edges_added": result["edges_added"],
        })

    # Check refresh timestamps again
    has_timestamps_after, timestamps_after = check_refresh_timestamps(db_path)
    if has_timestamps_after:
        print(f"Found {len(timestamps_after)} refresh timestamps after build")
    else:
        print("No refresh timestamps found after build")

    benchmark_results.update({
        "has_timestamps_after": has_timestamps_after,
        "timestamp_count_after": len(timestamps_after) if has_timestamps_after else 0,
    })

    return benchmark_results

def main():
    """Main function to run the benchmark."""
    # Check if --force-full flag is provided
    force_full = "--force-full" in sys.argv

    # Run the benchmark
    results = run_benchmark(force_full=force_full)

    # Print summary
    print("\n" + "="*50)
    print("BENCHMARK SUMMARY")
    print("="*50)
    print(f"Build Type: {results['build_type']}")
    print(f"Elapsed Time: {results['elapsed_time']:.2f} seconds")
    print(f"Nodes Added: {results['nodes_added']}")
    print(f"Edges Added: {results['edges_added']}")

    # Calculate nodes/second and edges/second
    nodes_per_second = results['nodes_added'] / results['elapsed_time'] if results['elapsed_time'] > 0 else 0
    edges_per_second = (
        results['edges_added'] / results['elapsed_time']
        if results['elapsed_time'] > 0 else 0
    )
    print(f"Nodes/Second: {nodes_per_second:.2f}")
    print(f"Edges/Second: {edges_per_second:.2f}")

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"benchmark_results_{results['build_type']}_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nBenchmark results saved to {results_file}")

if __name__ == "__main__":
    main()
