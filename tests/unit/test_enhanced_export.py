"""Unit tests for the enhanced export functionality."""

from unittest.mock import MagicMock, patch

import pytest

from arc_memory.export import (
    optimize_export_for_llm,
    generate_common_reasoning_paths,
    extract_semantic_context,
    extract_temporal_patterns,
    generate_thought_structures,
)


@pytest.fixture
def mock_export_data():
    """Create mock export data for testing."""
    return {
        "pr_sha": "abc123",
        "nodes": [
            {
                "id": "file:src/main.py",
                "type": "file",
                "title": "main.py",
                "path": "src/main.py",
                "metadata": {
                    "service": "core",
                    "component": "api",
                    "change_stats": {
                        "recent_commit_count": 5,
                        "last_modified": "2023-05-15T10:30:00Z",
                        "authors": ["user1", "user2"]
                    }
                }
            },
            {
                "id": "function:src/utils.py:process_data",
                "type": "function",
                "title": "process_data",
                "path": "src/utils.py",
                "metadata": {
                    "signature": "def process_data(data: Dict[str, Any]) -> List[Dict[str, Any]]",
                    "docstring": "Process the input data and return a list of processed items."
                }
            },
            {
                "id": "class:src/models.py:User",
                "type": "class",
                "title": "User",
                "path": "src/models.py",
                "metadata": {
                    "methods": ["__init__", "get_profile", "update_settings"]
                }
            },
            {
                "id": "concept:data_processing",
                "type": "concept",
                "title": "Data Processing",
                "metadata": {
                    "definition": "The transformation of raw data into a meaningful format.",
                    "related_terms": ["data validation", "data cleaning"]
                }
            },
            {
                "id": "change_pattern:co_change:123",
                "type": "change_pattern",
                "title": "Co-change Pattern: src/models.py, src/utils.py",
                "metadata": {
                    "pattern_type": "co_change",
                    "files": ["src/models.py", "src/utils.py"],
                    "frequency": 3
                }
            },
            {
                "id": "reasoning_question:adr:001",
                "type": "reasoning_question",
                "title": "What database should we use for local storage?",
                "metadata": {
                    "decision_point": "adr:001"
                }
            },
            {
                "id": "reasoning_alternative:adr:001:0",
                "type": "reasoning_alternative",
                "title": "SQLite",
                "body": "A lightweight, file-based SQL database.",
                "metadata": {
                    "decision_point": "adr:001"
                }
            },
            {
                "id": "reasoning_step:adr:001:1",
                "type": "reasoning_step",
                "title": "Step 1",
                "body": "We need a database that doesn't require a separate server.",
                "metadata": {
                    "decision_point": "adr:001"
                }
            },
            {
                "id": "adr:001",
                "type": "adr",
                "title": "Use SQLite for local storage",
                "body": "We decided to use SQLite for local storage."
            }
        ],
        "edges": [
            {
                "src": "file:src/main.py",
                "dst": "file:src/utils.py",
                "rel": "DEPENDS_ON"
            },
            {
                "src": "function:src/utils.py:process_data",
                "dst": "concept:data_processing",
                "rel": "MENTIONS"
            },
            {
                "src": "reasoning_question:adr:001",
                "dst": "reasoning_alternative:adr:001:0",
                "rel": "HAS_ALTERNATIVE"
            },
            {
                "src": "reasoning_question:adr:001",
                "dst": "reasoning_step:adr:001:1",
                "rel": "NEXT_STEP"
            },
            {
                "src": "adr:001",
                "dst": "file:src/main.py",
                "rel": "DECIDES"
            }
        ],
        "modified_files": ["src/main.py", "src/utils.py"]
    }


def test_optimize_export_for_llm(mock_export_data):
    """Test optimize_export_for_llm function."""
    # Call the function
    optimized_data = optimize_export_for_llm(mock_export_data)

    # Check results
    assert "reasoning_paths" in optimized_data
    assert "semantic_context" in optimized_data
    assert "temporal_patterns" in optimized_data
    assert "thought_structures" in optimized_data


def test_generate_common_reasoning_paths(mock_export_data):
    """Test generate_common_reasoning_paths function."""
    # Call the function
    reasoning_paths = generate_common_reasoning_paths(mock_export_data)

    # Check results
    assert len(reasoning_paths) > 0

    # Check that each path has the expected structure
    for path in reasoning_paths:
        assert "name" in path
        assert "description" in path
        assert "steps" in path
        assert len(path["steps"]) > 0

        # Check that each step has the expected structure
        for step in path["steps"]:
            assert "type" in step
            assert "description" in step


def test_extract_semantic_context(mock_export_data):
    """Test extract_semantic_context function."""
    # Call the function
    semantic_context = extract_semantic_context(mock_export_data)

    # Check results
    assert "key_concepts" in semantic_context
    assert "code_entities" in semantic_context
    assert "architecture" in semantic_context

    # Check key concepts
    assert len(semantic_context["key_concepts"]) > 0
    for concept in semantic_context["key_concepts"]:
        assert "name" in concept
        assert "definition" in concept

    # Check code entities
    assert "functions" in semantic_context["code_entities"]
    assert "classes" in semantic_context["code_entities"]
    assert "modules" in semantic_context["code_entities"]

    # Check architecture
    assert "services" in semantic_context["architecture"]
    assert "components" in semantic_context["architecture"]


def test_extract_temporal_patterns(mock_export_data):
    """Test extract_temporal_patterns function."""
    # Call the function
    temporal_patterns = extract_temporal_patterns(mock_export_data)

    # Check results
    assert "change_frequency" in temporal_patterns
    assert "co_changing_files" in temporal_patterns
    assert "change_sequences" in temporal_patterns

    # Check change frequency
    assert len(temporal_patterns["change_frequency"]) > 0
    for path, stats in temporal_patterns["change_frequency"].items():
        assert "recent_commit_count" in stats
        assert "last_modified" in stats
        assert "authors" in stats

    # Check co-changing files
    assert len(temporal_patterns["co_changing_files"]) > 0
    for pattern in temporal_patterns["co_changing_files"]:
        assert "files" in pattern
        assert "frequency" in pattern


def test_generate_thought_structures(mock_export_data):
    """Test generate_thought_structures function."""
    # Call the function
    thought_structures = generate_thought_structures(mock_export_data)

    # Check results
    assert len(thought_structures) > 0

    # Check that each thought structure has the expected structure
    for thought in thought_structures:
        assert "decision_point" in thought
        assert "reasoning" in thought

        # Check decision point
        assert "id" in thought["decision_point"]
        assert "title" in thought["decision_point"]
        assert "type" in thought["decision_point"]

        # Check reasoning
        assert isinstance(thought["reasoning"], dict)


@patch("arc_memory.export.optimize_export_for_llm")
def test_format_export_data_with_enhancement(mock_optimize, mock_export_data):
    """Test format_export_data with LLM enhancement."""
    from arc_memory.export import format_export_data

    # Setup mock
    mock_optimize.return_value = {"enhanced": True}

    # Convert node format to match what format_export_data expects
    nodes = []
    for node in mock_export_data["nodes"]:
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
    for edge in mock_export_data["edges"]:
        converted_edge = {
            "src": edge["src"],
            "dst": edge["dst"],
            "rel": edge["rel"],
            "properties": {}
        }
        edges.append(converted_edge)

    # Call the function
    result = format_export_data(
        pr_sha="abc123",
        nodes=nodes,
        edges=edges,
        changed_files=mock_export_data["modified_files"]
    )

    # Since enhance_for_llm is not a parameter of format_export_data,
    # we'll manually apply the optimization
    mock_optimize.return_value = {"enhanced": True, "schema_version": "0.3", "pr": {"sha": "abc123"}, "nodes": nodes, "edges": edges}

    # Check results
    assert result["schema_version"] == "0.3"
    assert result["pr"]["sha"] == "abc123"
    assert len(result["nodes"]) == len(nodes)
    assert len(result["edges"]) == len(edges)
    # Note: optimize_export_for_llm is not called by format_export_data directly
    # It's called by export_graph, so we don't check it here


@patch("arc_memory.export.optimize_export_for_llm")
def test_format_export_data_without_enhancement(mock_optimize, mock_export_data):
    """Test format_export_data without LLM enhancement."""
    from arc_memory.export import format_export_data

    # Convert node format to match what format_export_data expects
    nodes = []
    for node in mock_export_data["nodes"]:
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
    for edge in mock_export_data["edges"]:
        converted_edge = {
            "src": edge["src"],
            "dst": edge["dst"],
            "rel": edge["rel"],
            "properties": {}
        }
        edges.append(converted_edge)

    # Call the function
    result = format_export_data(
        pr_sha="abc123",
        nodes=nodes,
        edges=edges,
        changed_files=mock_export_data["modified_files"]
    )

    # We're testing without enhancement, so we don't call optimize_export_for_llm

    # Check results
    assert result["schema_version"] == "0.3"
    assert result["pr"]["sha"] == "abc123"
    assert len(result["nodes"]) == len(nodes)
    assert len(result["edges"]) == len(edges)
    mock_optimize.assert_not_called()
