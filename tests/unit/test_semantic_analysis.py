"""Unit tests for the semantic analysis module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arc_memory.process.semantic_analysis import (
    enhance_with_semantic_analysis,
    extract_key_concepts,
    infer_semantic_relationships,
    detect_architecture,
)
from arc_memory.schema.models import ConceptNode, Edge, EdgeRel, Node, NodeType


@pytest.fixture
def mock_nodes():
    """Create mock nodes for testing."""
    return [
        Node(
            id="file:src/main.py",
            type=NodeType.FILE,
            title="main.py",
            body="This is the main module for the application.",
        ),
        Node(
            id="file:src/utils.py",
            type=NodeType.FILE,
            title="utils.py",
            body="Utility functions for data processing and validation.",
        ),
        Node(
            id="commit:abc123",
            type=NodeType.COMMIT,
            title="Add data processing functions",
            body="This commit adds several functions for processing user data.",
        ),
    ]


@pytest.fixture
def mock_edges():
    """Create mock edges for testing."""
    return [
        Edge(
            src="commit:abc123",
            dst="file:src/utils.py",
            rel=EdgeRel.MODIFIES,
        ),
        Edge(
            src="file:src/main.py",
            dst="file:src/utils.py",
            rel=EdgeRel.DEPENDS_ON,
        ),
    ]


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client."""
    client = MagicMock()
    client.generate.return_value = json.dumps({
        "concepts": [
            {
                "name": "Data Processing",
                "definition": "The transformation of raw data into a meaningful format.",
                "related_terms": ["data validation", "data cleaning"]
            },
            {
                "name": "Application Architecture",
                "definition": "The structure and organization of the application's components.",
                "related_terms": ["modules", "dependencies"]
            }
        ]
    })
    return client


@patch("arc_memory.process.semantic_analysis.OllamaClient")
def test_enhance_with_semantic_analysis_fast(mock_ollama_client_class, mock_nodes, mock_edges):
    """Test enhance_with_semantic_analysis with fast enhancement level."""
    # Setup mock
    mock_client = MagicMock()
    mock_ollama_client_class.return_value = mock_client

    # Mock the extract_key_concepts function
    mock_concept_nodes = [
        ConceptNode(
            id="concept:data_processing",
            type=NodeType.CONCEPT,
            title="Data Processing",
            name="Data Processing",
            definition="The transformation of raw data into a meaningful format.",
            related_terms=["data validation", "data cleaning"],
        )
    ]
    mock_concept_edges = [
        Edge(
            src="file:src/utils.py",
            dst="concept:data_processing",
            rel=EdgeRel.MENTIONS,
            properties={"confidence": 0.8},
        )
    ]

    with patch(
        "arc_memory.process.semantic_analysis.extract_key_concepts",
        return_value=(mock_concept_nodes, mock_concept_edges),
    ):
        # Call the function
        enhanced_nodes, enhanced_edges = enhance_with_semantic_analysis(
            mock_nodes, mock_edges, enhancement_level="fast"
        )

        # Check results
        assert len(enhanced_nodes) == len(mock_nodes) + len(mock_concept_nodes)
        assert len(enhanced_edges) == len(mock_edges) + len(mock_concept_edges)

        # Check that the concept node was added
        concept_node = next(
            (n for n in enhanced_nodes if n.type == NodeType.CONCEPT), None
        )
        assert concept_node is not None
        assert concept_node.name == "Data Processing"


@patch("arc_memory.process.semantic_analysis.OllamaClient")
def test_enhance_with_semantic_analysis_standard(
    mock_ollama_client_class, mock_nodes, mock_edges
):
    """Test enhance_with_semantic_analysis with standard enhancement level."""
    # Setup mock
    mock_client = MagicMock()
    mock_ollama_client_class.return_value = mock_client

    # Mock the extract_key_concepts function
    mock_concept_nodes = [
        ConceptNode(
            id="concept:data_processing",
            type=NodeType.CONCEPT,
            title="Data Processing",
            name="Data Processing",
            definition="The transformation of raw data into a meaningful format.",
            related_terms=["data validation", "data cleaning"],
        )
    ]
    mock_concept_edges = [
        Edge(
            src="file:src/utils.py",
            dst="concept:data_processing",
            rel=EdgeRel.MENTIONS,
            properties={"confidence": 0.8},
        )
    ]

    # Mock the infer_semantic_relationships function
    mock_relationship_edges = [
        Edge(
            src="concept:data_processing",
            dst="concept:application_architecture",
            rel=EdgeRel.MENTIONS,  # Use an existing edge type
            properties={"confidence": 0.7},
        )
    ]

    with patch(
        "arc_memory.process.semantic_analysis.extract_key_concepts",
        return_value=(mock_concept_nodes, mock_concept_edges),
    ), patch(
        "arc_memory.process.semantic_analysis.infer_semantic_relationships",
        return_value=mock_relationship_edges,
    ):
        # Call the function
        enhanced_nodes, enhanced_edges = enhance_with_semantic_analysis(
            mock_nodes, mock_edges, enhancement_level="standard"
        )

        # Check results
        assert len(enhanced_nodes) == len(mock_nodes) + len(mock_concept_nodes)
        assert len(enhanced_edges) == len(mock_edges) + len(mock_concept_edges) + len(mock_relationship_edges)


def test_extract_key_concepts(mock_ollama_client, mock_nodes, mock_edges):
    """Test extract_key_concepts function."""
    # Call the function
    concept_nodes, concept_edges = extract_key_concepts(
        mock_nodes, mock_edges, mock_ollama_client
    )

    # Check results
    assert len(concept_nodes) == 2
    assert all(node.type == NodeType.CONCEPT for node in concept_nodes)
    assert any(node.name == "Data Processing" for node in concept_nodes)
    assert any(node.name == "Application Architecture" for node in concept_nodes)

    # Check edges
    assert len(concept_edges) > 0
    assert all(edge.rel == EdgeRel.MENTIONS for edge in concept_edges)


def test_infer_semantic_relationships():
    """Test infer_semantic_relationships function."""
    # This is a placeholder test since the function is a placeholder
    nodes = [
        ConceptNode(
            id="concept:data_processing",
            type=NodeType.CONCEPT,
            title="Data Processing",
            name="Data Processing",
            definition="The transformation of raw data into a meaningful format.",
        ),
        ConceptNode(
            id="concept:application_architecture",
            type=NodeType.CONCEPT,
            title="Application Architecture",
            name="Application Architecture",
            definition="The structure and organization of the application's components.",
        ),
    ]
    edges = []

    # Call the function
    relationship_edges = infer_semantic_relationships(nodes, edges, MagicMock())

    # Check results (currently returns an empty list)
    assert isinstance(relationship_edges, list)


def test_detect_architecture():
    """Test detect_architecture function."""
    # This is a placeholder test since the function is a placeholder
    nodes = []
    edges = []

    # Call the function
    architecture_nodes, architecture_edges = detect_architecture(
        nodes, edges, Path("/fake/repo"), MagicMock()
    )

    # Check results (currently returns empty lists)
    assert isinstance(architecture_nodes, list)
    assert isinstance(architecture_edges, list)
