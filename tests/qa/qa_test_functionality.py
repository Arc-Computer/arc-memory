#!/usr/bin/env python
"""
QA Test Script for Arc Memory SDK Core Functionality.

This script tests the core functionality of the Arc Memory SDK.
It verifies that the SDK can perform basic operations like querying,
getting decision trails, and analyzing component impact.

Usage:
    python qa_test_functionality.py
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Import Arc Memory SDK
try:
    from arc_memory import Arc
    from arc_memory.sdk.errors import QueryError, AdapterError, SDKError
except ImportError as e:
    print(f"❌ Failed to import Arc Memory SDK: {e}")
    print("Please install Arc Memory SDK first: pip install arc-memory[all]")
    sys.exit(1)

# Initialize Arc
try:
    repo_path = Path.cwd()
    arc = Arc(repo_path=repo_path)
    print(f"✅ Successfully initialized Arc with repository path: {repo_path}")
except Exception as e:
    print(f"❌ Failed to initialize Arc: {e}")
    sys.exit(1)

# Test 1: Check if graph exists
print("\nTest 1: Checking if graph exists...")
try:
    node_count = arc.get_node_count()
    print(f"✅ Graph exists with {node_count} nodes")

    if node_count == 0:
        print("⚠️ Graph is empty. Run 'arc build' to build the knowledge graph.")
        print("Skipping remaining tests that require a built graph.")
        sys.exit(0)
except Exception as e:
    print(f"❌ Failed to check if graph exists: {e}")
    sys.exit(1)

# Test 2: Test query functionality
print("\nTest 2: Testing query functionality...")
try:
    # Use a generic question that should work with any repository
    question = "What are the main components of this repository?"
    print(f"Querying: '{question}'")

    start_time = time.time()
    result = arc.query(question=question, max_results=3, max_hops=2)
    elapsed_time = time.time() - start_time

    print(f"✅ Query completed in {elapsed_time:.2f} seconds")
    print(f"Answer: {result.answer[:100]}..." if len(result.answer) > 100 else f"Answer: {result.answer}")
    print(f"Confidence: {result.confidence}")
    print(f"Evidence count: {len(result.evidence)}")
except Exception as e:
    print(f"❌ Failed to test query functionality: {e}")

# Test 3: Test getting a node by ID
print("\nTest 3: Testing get_node_by_id functionality...")
try:
    # Get a sample node ID from the graph
    # This is a bit of a hack, but it should work for most repositories
    # We're looking for a commit node, which should exist in any Git repository
    from arc_memory.schema.models import NodeType

    # Query for commit nodes
    query = f"SELECT id FROM nodes WHERE type = '{NodeType.COMMIT.value}' LIMIT 1"
    result = arc.adapter.execute_query(query)

    if result and len(result) > 0:
        node_id = result[0][0]
        print(f"Found node ID: {node_id}")

        # Get the node
        node = arc.get_node_by_id(node_id)
        if node:
            print(f"✅ Successfully got node: {node.get('title', 'No title')}")
        else:
            print("❌ Node not found")
    else:
        print("⚠️ No commit nodes found in the graph")
except Exception as e:
    print(f"❌ Failed to test get_node_by_id functionality: {e}")

# Test 4: Test getting decision trail
print("\nTest 4: Testing get_decision_trail functionality...")
try:
    # Find a file in the repository
    import os

    # Look for Python files in the repository
    python_files = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                python_files.append(rel_path)
                if len(python_files) >= 5:  # Limit to 5 files
                    break
        if len(python_files) >= 5:
            break

    if python_files:
        file_path = python_files[0]
        line_number = 1  # Use line 1 as a default

        print(f"Getting decision trail for {file_path}:{line_number}")

        start_time = time.time()
        decision_trail = arc.get_decision_trail(file_path=file_path, line_number=line_number, max_results=3)
        elapsed_time = time.time() - start_time

        print(f"✅ Decision trail retrieved in {elapsed_time:.2f} seconds")
        print(f"Decision trail entries: {len(decision_trail)}")

        if decision_trail:
            for i, entry in enumerate(decision_trail):
                print(f"  Entry {i+1}: {entry.title} ({entry.type})")
        else:
            print("  No decision trail entries found")
    else:
        print("⚠️ No Python files found in the repository")
except Exception as e:
    print(f"❌ Failed to test get_decision_trail functionality: {e}")

# Test 5: Test getting related entities
print("\nTest 5: Testing get_related_entities functionality...")
try:
    # Use the same node ID from Test 3
    query = f"SELECT id FROM nodes WHERE type = '{NodeType.COMMIT.value}' LIMIT 1"
    result = arc.adapter.execute_query(query)

    if result and len(result) > 0:
        node_id = result[0][0]
        print(f"Getting related entities for node ID: {node_id}")

        start_time = time.time()
        related_entities = arc.get_related_entities(entity_id=node_id, max_results=5)
        elapsed_time = time.time() - start_time

        print(f"✅ Related entities retrieved in {elapsed_time:.2f} seconds")
        print(f"Related entities count: {len(related_entities)}")

        if related_entities:
            for i, entity in enumerate(related_entities):
                print(f"  Entity {i+1}: {entity.title} ({entity.type}) - {entity.relationship}")
        else:
            print("  No related entities found")
    else:
        print("⚠️ No commit nodes found in the graph")
except Exception as e:
    print(f"❌ Failed to test get_related_entities functionality: {e}")

# Helper function for component impact analysis
def analyze_component_impact_and_print_results(component_id, max_depth=2):
    """Analyze component impact and print the results.

    Args:
        component_id: The ID of the component to analyze.
        max_depth: Maximum depth of indirect dependency analysis.

    Returns:
        True if analysis was successful, False otherwise.
    """
    try:
        print(f"Analyzing component impact for: {component_id}")

        start_time = time.time()
        impact_results = arc.analyze_component_impact(component_id=component_id, max_depth=max_depth)
        elapsed_time = time.time() - start_time

        print(f"✅ Component impact analysis completed in {elapsed_time:.2f} seconds")
        print(f"Impact results count: {len(impact_results)}")

        if impact_results:
            for i, result in enumerate(impact_results):
                print(f"  Result {i+1}: {result.title} - Impact score: {result.impact_score} ({result.impact_type})")
        else:
            print("  No impact results found")
        return True
    except Exception as e:
        print(f"❌ Failed to analyze component impact: {e}")
        return False

# Test 6: Test component impact analysis
print("\nTest 6: Testing analyze_component_impact functionality...")
try:
    # Use a Python file from the repository that we know exists
    try:
        # Try to find a file that exists in the knowledge graph
        query = "SELECT id FROM nodes WHERE type = 'file' AND id LIKE 'file:%.py' LIMIT 1"
        result = arc.adapter.execute_query(query)

        if result and len(result) > 0:
            component_id = result[0][0]
            analyze_component_impact_and_print_results(component_id)
        else:
            print("⚠️ No Python files found in the knowledge graph")
    except Exception as e:
        print(f"⚠️ Error finding Python files in the knowledge graph: {e}")
        # Fall back to using a Python file from Test 4
        if python_files:
            file_path = python_files[0]
            component_id = f"file:{file_path}"

            print(f"Falling back to analyzing component impact for: {component_id}")
            analyze_component_impact_and_print_results(component_id)
        else:
            print("⚠️ No Python files found in the repository")
except Exception as e:
    print(f"❌ Failed to test analyze_component_impact functionality: {e}")

# Test 7: Test export functionality
print("\nTest 7: Testing export_graph functionality...")
try:
    # Get the latest commit SHA
    import subprocess
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)

    if result.returncode == 0:
        commit_sha = result.stdout.strip()
        output_path = Path("test_export.json")

        print(f"Exporting graph for commit SHA: {commit_sha}")

        try:
            # Make sure the adapter has a connection
            if not hasattr(arc.adapter, "connection") or not arc.adapter.connection:
                # Try to reconnect
                print("Database connection not available, attempting to reconnect...")
                if hasattr(arc.adapter, "db_path") and arc.adapter.db_path:
                    arc.adapter.connect({"db_path": str(arc.adapter.db_path)})
                    print(f"Reconnected to database: {arc.adapter.db_path}")
                else:
                    print("Cannot reconnect: db_path not available")
                    raise Exception("Database connection not available and cannot reconnect")

            start_time = time.time()
            export_result = arc.export_graph(
                pr_sha=commit_sha,
                output_path=output_path,
                compress=True,
                max_hops=2
            )
            elapsed_time = time.time() - start_time

            print(f"✅ Graph export completed in {elapsed_time:.2f} seconds")
            print(f"Export saved to: {export_result.output_path}")
            print(f"Entity count: {export_result.entity_count}")
            print(f"Relationship count: {export_result.relationship_count}")

            # Clean up the export file
            output_file = Path(export_result.output_path)
            if output_file.exists():
                output_file.unlink()
                print(f"Cleaned up export file: {output_file}")

            # Clean up the original output path if it exists and is different
            if output_path.exists() and output_path != output_file:
                output_path.unlink()
                print(f"Cleaned up original export file: {output_path}")
        except Exception as e:
            print(f"❌ Error during export: {e}")
            # Try a simpler approach with minimal parameters
            try:
                print("Trying simplified export...")
                output_path = Path("simple_export.json")
                export_result = arc.export_graph(
                    pr_sha=commit_sha,
                    output_path=output_path,
                    compress=False,
                    max_hops=1,
                    optimize_for_llm=False,
                    include_causal=False
                )
                print(f"✅ Simplified export completed successfully")
                print(f"Export saved to: {export_result.output_path}")

                # Clean up the export file
                output_file = Path(export_result.output_path)
                if output_file.exists():
                    output_file.unlink()
                    print(f"Cleaned up export file: {output_file}")
            except Exception as e2:
                print(f"❌ Simplified export also failed: {e2}")
    else:
        print(f"⚠️ Failed to get latest commit SHA: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test export_graph functionality: {e}")

# Summary
print("\n=== Test Summary ===")
print("Arc Memory SDK core functionality tests completed.")
print("Run 'python qa_test_adapters.py' to test framework adapters.")
