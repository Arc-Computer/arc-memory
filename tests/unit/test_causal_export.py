"""Unit tests for the causal relationship export functionality."""

from unittest.mock import MagicMock, patch

import pytest

from arc_memory.export import (
    extract_causal_relationships,
    optimize_export_for_llm,
    generate_common_reasoning_paths,
    format_export_data,
)
from arc_memory.schema.models import NodeType, EdgeRel


@pytest.fixture
def mock_causal_export_data():
    """Create mock export data with causal relationships for testing."""
    return {
        "pr_sha": "abc123",
        "nodes": [
            {
                "id": "decision:123",
                "type": "decision",
                "title": "Use SQLite for local storage",
                "body": "We decided to use SQLite for local storage because it's lightweight.",
                "metadata": {
                    "decision_type": "architectural",
                    "confidence": 0.9,
                    "decision_makers": ["user1"]
                }
            },
            {
                "id": "implication:456",
                "type": "implication",
                "title": "Limited concurrent connections",
                "body": "SQLite has limitations on concurrent connections.",
                "metadata": {
                    "implication_type": "technical",
                    "severity": "medium",
                    "confidence": 0.8,
                    "source": "decision:123"
                }
            },
            {
                "id": "code_change:789",
                "type": "code_change",
                "title": "Implement connection pooling",
                "body": "Added connection pooling to mitigate SQLite connection limits.",
                "metadata": {
                    "change_type": "feature",
                    "files": ["src/db/connection_pool.py"],
                    "description": "Implemented a connection pool to manage SQLite connections.",
                    "confidence": 0.85,
                    "source": "implication:456"
                }
            },
            {
                "id": "file:src/db/connection_pool.py",
                "type": "file",
                "path": "src/db/connection_pool.py",
                "metadata": {
                    "service": "db",
                    "component": "storage"
                }
            }
        ],
        "edges": [
            {
                "src": "decision:123",
                "dst": "implication:456",
                "type": "LEADS_TO",
                "metadata": {
                    "confidence": 0.9,
                    "extraction_method": "rule_based"
                }
            },
            {
                "src": "implication:456",
                "dst": "code_change:789",
                "type": "RESULTS_IN",
                "metadata": {
                    "confidence": 0.85,
                    "extraction_method": "llm"
                }
            },
            {
                "src": "code_change:789",
                "dst": "file:src/db/connection_pool.py",
                "type": "MODIFIES",
                "metadata": {
                    "confidence": 1.0
                }
            }
        ],
        "modified_files": ["src/db/connection_pool.py"]
    }


def test_extract_causal_relationships(mock_causal_export_data):
    """Test extract_causal_relationships function."""
    # Call the function
    causal_relationships = extract_causal_relationships(mock_causal_export_data)

    # Check results
    assert "decision_chains" in causal_relationships
    assert "implications" in causal_relationships
    assert "code_changes" in causal_relationships
    assert "causal_edges" in causal_relationships

    # Check decision chains
    assert len(causal_relationships["decision_chains"]) == 1
    decision_chain = causal_relationships["decision_chains"][0]
    assert decision_chain["id"] == "decision:123"
    assert decision_chain["title"] == "Use SQLite for local storage"
    assert decision_chain["type"] == "architectural"
    assert decision_chain["confidence"] == 0.9

    # Check implications in decision chain
    assert len(decision_chain["implications"]) == 1
    implication = decision_chain["implications"][0]
    assert implication["id"] == "implication:456"
    assert implication["title"] == "Limited concurrent connections"
    assert implication["type"] == "technical"
    assert implication["severity"] == "medium"

    # Check code changes in decision chain
    assert len(decision_chain["code_changes"]) == 1
    code_change = decision_chain["code_changes"][0]
    assert code_change["id"] == "code_change:789"
    assert code_change["title"] == "Implement connection pooling"
    assert code_change["type"] == "feature"
    assert "files" in code_change

    # Check causal edges
    assert len(causal_relationships["causal_edges"]) >= 2
    edge_types = [edge["type"] for edge in causal_relationships["causal_edges"]]
    assert "LEADS_TO" in edge_types
    assert "RESULTS_IN" in edge_types


def test_generate_common_reasoning_paths_with_causal_paths(mock_causal_export_data):
    """Test that generate_common_reasoning_paths includes causal reasoning paths."""
    # Call the function
    reasoning_paths = generate_common_reasoning_paths(mock_causal_export_data)

    # Check results
    assert len(reasoning_paths) >= 4  # At least 4 paths (including causal paths)

    # Check for causal chain analysis path
    causal_chain_path = next((p for p in reasoning_paths if p["name"] == "causal_chain_analysis"), None)
    assert causal_chain_path is not None
    assert "LEADS_TO" in str(causal_chain_path["steps"])
    assert "RESULTS_IN" in str(causal_chain_path["steps"])

    # Check for implication analysis path
    implication_path = next((p for p in reasoning_paths if p["name"] == "implication_analysis"), None)
    assert implication_path is not None
    assert "severity" in str(implication_path["steps"])

    # Check for reverse causal analysis path
    reverse_path = next((p for p in reasoning_paths if p["name"] == "reverse_causal_analysis"), None)
    assert reverse_path is not None
    assert "CAUSED_BY" in str(reverse_path["steps"])


def test_optimize_export_for_llm_with_causal_relationships(mock_causal_export_data):
    """Test that optimize_export_for_llm includes causal relationships."""
    # Call the function
    optimized_data = optimize_export_for_llm(mock_causal_export_data)

    # Check results
    assert "causal_relationships" in optimized_data
    assert "decision_chains" in optimized_data["causal_relationships"]
    assert "implications" in optimized_data["causal_relationships"]
    assert "code_changes" in optimized_data["causal_relationships"]

    # Check that reasoning paths include causal paths
    assert "reasoning_paths" in optimized_data
    path_names = [p["name"] for p in optimized_data["reasoning_paths"]]
    assert "causal_chain_analysis" in path_names
    assert "implication_analysis" in path_names
    assert "reverse_causal_analysis" in path_names


def test_format_export_data_with_causal_nodes(mock_causal_export_data):
    """Test format_export_data with causal relationship nodes."""
    # Convert node format to match what format_export_data expects
    nodes = []
    for node in mock_causal_export_data["nodes"]:
        converted_node = {
            "id": node["id"],
            "type": node["type"],
            "title": node.get("title", ""),
            "body": node.get("body", ""),
            "extra": {}
        }
        # Move metadata and other fields to extra
        if "metadata" in node:
            converted_node["extra"].update(node["metadata"])
        if "path" in node:
            converted_node["extra"]["path"] = node["path"]
        nodes.append(converted_node)

    # Convert edge format
    edges = []
    for edge in mock_causal_export_data["edges"]:
        converted_edge = {
            "src": edge["src"],
            "dst": edge["dst"],
            "rel": edge["type"],
            "properties": edge.get("metadata", {})
        }
        edges.append(converted_edge)

    # Call the function
    result = format_export_data(
        pr_sha="abc123",
        nodes=nodes,
        edges=edges,
        changed_files=mock_causal_export_data["modified_files"],
    )

    # Check results
    assert result["schema_version"] == "0.3"  # Check for updated schema version

    # Check that causal nodes are properly formatted
    decision_node = next((n for n in result["nodes"] if n["id"] == "decision:123"), None)
    assert decision_node is not None
    assert "decision_type" in decision_node["metadata"]
    assert "confidence" in decision_node["metadata"]

    implication_node = next((n for n in result["nodes"] if n["id"] == "implication:456"), None)
    assert implication_node is not None
    assert "implication_type" in implication_node["metadata"]
    assert "severity" in implication_node["metadata"]

    code_change_node = next((n for n in result["nodes"] if n["id"] == "code_change:789"), None)
    assert code_change_node is not None
    assert "change_type" in code_change_node["metadata"]
    assert "files" in code_change_node["metadata"]
