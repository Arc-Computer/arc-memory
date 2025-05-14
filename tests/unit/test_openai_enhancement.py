#!/usr/bin/env python3
"""
Test script for OpenAI integration with Arc Memory.

This script tests building a knowledge graph with OpenAI enhancement
and compares the graph density with and without enhancement.

Usage:
    python test_openai_enhancement.py --repo-path /path/to/repo

Requirements:
    - Arc Memory installed: pip install arc-memory[openai]
    - OpenAI API key: export OPENAI_API_KEY=your-key
"""

import os
import sys
import time
import argparse
import tempfile
from pathlib import Path

from arc_memory import Arc
from arc_memory.auto_refresh import refresh_knowledge_graph
from arc_memory.sql.db import init_db, get_node_count, get_edge_count


def test_openai_enhancement(repo_path, model="gpt-4.1"):
    """
    Test building a knowledge graph with OpenAI enhancement.

    Args:
        repo_path: Path to the repository
        model: OpenAI model to use

    Returns:
        A tuple of (without_enhancement, with_enhancement) results
    """
    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY=your-api-key")
        sys.exit(1)

    # Create temporary databases for testing
    temp_dir = tempfile.mkdtemp()
    db_path_without = Path(temp_dir) / "without_enhancement.db"
    db_path_with = Path(temp_dir) / "with_enhancement.db"

    print(f"Testing OpenAI enhancement with model: {model}")
    print(f"Repository path: {repo_path}")
    print(f"Temporary directory: {temp_dir}")

    # Build knowledge graph without enhancement
    print("\n=== Building knowledge graph without enhancement ===")
    start_time = time.time()
    refresh_result_without = refresh_knowledge_graph(
        repo_path=repo_path,
        db_path=db_path_without,  # Pass Path object directly
        include_github=True,
        include_linear=False,
        use_llm=False,
        verbose=True
    )
    elapsed_without = time.time() - start_time

    # Get graph statistics without enhancement
    conn_without = init_db(db_path=db_path_without)
    node_count_without = get_node_count(conn_without)
    edge_count_without = get_edge_count(conn_without)

    print(f"\nWithout enhancement:")
    print(f"  Build time: {elapsed_without:.2f} seconds")
    print(f"  Nodes: {node_count_without}")
    print(f"  Edges: {edge_count_without}")
    print(f"  Edge/Node ratio: {edge_count_without / node_count_without:.2f}")

    # Build knowledge graph with enhancement
    print("\n=== Building knowledge graph with OpenAI enhancement ===")
    start_time = time.time()
    refresh_result_with = refresh_knowledge_graph(
        repo_path=repo_path,
        db_path=db_path_with,  # Pass Path object directly
        include_github=True,
        include_linear=True,
        use_llm=True,
        llm_provider="openai",
        llm_model=model,
        verbose=True
    )
    elapsed_with = time.time() - start_time

    # Get graph statistics with enhancement
    conn_with = init_db(db_path=db_path_with)
    node_count_with = get_node_count(conn_with)
    edge_count_with = get_edge_count(conn_with)

    print(f"\nWith enhancement:")
    print(f"  Build time: {elapsed_with:.2f} seconds")
    print(f"  Nodes: {node_count_with}")
    print(f"  Edges: {edge_count_with}")
    print(f"  Edge/Node ratio: {edge_count_with / node_count_with:.2f}")

    # Compare results
    node_increase = node_count_with - node_count_without
    edge_increase = edge_count_with - edge_count_without
    node_percent = (node_increase / node_count_without) * 100 if node_count_without > 0 else 0
    edge_percent = (edge_increase / edge_count_without) * 100 if edge_count_without > 0 else 0

    print("\n=== Comparison ===")
    print(f"Node increase: {node_increase} ({node_percent:.2f}%)")
    print(f"Edge increase: {edge_increase} ({edge_percent:.2f}%)")
    print(f"Build time increase: {elapsed_with - elapsed_without:.2f} seconds ({(elapsed_with / elapsed_without) * 100:.2f}%)")

    # Test querying with both graphs
    print("\n=== Testing queries ===")

    # Initialize Arc with both databases
    arc_without = Arc(repo_path=repo_path, connection_params={"db_path": str(db_path_without)})
    arc_with = Arc(repo_path=repo_path, connection_params={"db_path": str(db_path_with)})

    # Test query
    test_query = "What are the main components of this repository?"

    print(f"\nQuery: {test_query}")

    print("\nWithout enhancement:")
    result_without = arc_without.query(test_query)
    print(f"  Answer: {result_without.answer}")
    print(f"  Confidence: {result_without.confidence}")
    print(f"  Evidence count: {len(result_without.evidence)}")

    print("\nWith enhancement:")
    result_with = arc_with.query(test_query)
    print(f"  Answer: {result_with.answer}")
    print(f"  Confidence: {result_with.confidence}")
    print(f"  Evidence count: {len(result_with.evidence)}")

    return {
        "without_enhancement": {
            "build_time": elapsed_without,
            "node_count": node_count_without,
            "edge_count": edge_count_without,
            "edge_node_ratio": edge_count_without / node_count_without if node_count_without > 0 else 0,
            "query_result": result_without
        },
        "with_enhancement": {
            "build_time": elapsed_with,
            "node_count": node_count_with,
            "edge_count": edge_count_with,
            "edge_node_ratio": edge_count_with / node_count_with if node_count_with > 0 else 0,
            "query_result": result_with
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Test OpenAI enhancement for Arc Memory")
    parser.add_argument("--repo-path", default="./", help="Path to the repository")
    parser.add_argument("--model", default="gpt-4.1", help="OpenAI model to use")
    args = parser.parse_args()

    test_openai_enhancement(args.repo_path, args.model)


if __name__ == "__main__":
    main()
