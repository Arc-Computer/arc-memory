"""Unit tests for the Knowledge Graph of Thoughts (KGoT) module."""

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arc_memory.process.kgot import (
    KGoTProcessor,
    enhance_with_reasoning_structures,
)
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType


@pytest.fixture
def mock_nodes():
    """Create mock nodes for testing."""
    return [
        Node(
            id="adr:001",
            type=NodeType.ADR,
            title="Use SQLite for local storage",
            body="We decided to use SQLite for local storage because it's lightweight and doesn't require a separate server.",
        ),
        Node(
            id="pr:123",
            type=NodeType.PR,
            title="Implement SQLite storage",
            body="This PR implements the SQLite storage layer as decided in ADR-001.",
        ),
        Node(
            id="issue:456",
            type=NodeType.ISSUE,
            title="Choose database for local storage",
            body="We need to decide which database to use for local storage.",
        ),
        Node(
            id="commit:abc123",
            type=NodeType.COMMIT,
            title="Add SQLite implementation",
            body="Adds the SQLite implementation for local storage.",
        ),
        Node(
            id="file:src/storage.py",
            type=NodeType.FILE,
            title="storage.py",
            body="Implementation of the storage layer using SQLite.",
        ),
        Node(
            id="issue:789",
            type=NodeType.ISSUE,
            title="SQLite performance concerns",
            body="Are there any performance concerns with using SQLite?",
        ),
        Node(
            id="issue:101",
            type=NodeType.ISSUE,
            title="SQLite testing strategy",
            body="How should we test the SQLite implementation?",
        ),
    ]


@pytest.fixture
def mock_edges():
    """Create mock edges for testing."""
    return [
        Edge(
            src="adr:001",
            dst="file:src/storage.py",
            rel=EdgeRel.DECIDES,
        ),
        Edge(
            src="pr:123",
            dst="commit:abc123",
            rel=EdgeRel.MERGES,
        ),
        Edge(
            src="pr:123",
            dst="issue:456",
            rel=EdgeRel.MENTIONS,
        ),
        Edge(
            src="issue:456",
            dst="adr:001",
            rel=EdgeRel.MENTIONS,
        ),
        Edge(
            src="commit:abc123",
            dst="file:src/storage.py",
            rel=EdgeRel.MODIFIES,
        ),
        Edge(
            src="pr:123",
            dst="issue:789",
            rel=EdgeRel.MENTIONS,
        ),
        Edge(
            src="pr:123",
            dst="issue:101",
            rel=EdgeRel.MENTIONS,
        ),
    ]


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client."""
    client = MagicMock()
    client.generate.return_value = json.dumps({
        "question": "What database should we use for local storage?",
        "alternatives": [
            {
                "name": "SQLite",
                "description": "A lightweight, file-based SQL database."
            },
            {
                "name": "PostgreSQL",
                "description": "A powerful, open-source object-relational database system."
            }
        ],
        "criteria": [
            {
                "name": "Simplicity",
                "description": "How easy is it to set up and maintain?"
            },
            {
                "name": "Performance",
                "description": "How well does it perform for our use case?"
            }
        ],
        "reasoning": [
            {
                "step": 1,
                "description": "We need a database that doesn't require a separate server."
            },
            {
                "step": 2,
                "description": "SQLite is file-based and doesn't require a separate server."
            }
        ],
        "implications": [
            "We'll need to ensure proper file locking for concurrent access.",
            "We may need to migrate to a more powerful database if our needs grow."
        ]
    })
    return client


def test_kgot_processor_initialization():
    """Test that the KGoTProcessor initializes correctly."""
    processor = KGoTProcessor()
    assert processor.ollama_client is not None


@patch("arc_memory.process.kgot.OllamaClient")
def test_kgot_processor_with_custom_client(mock_ollama_client_class):
    """Test that the KGoTProcessor can be initialized with a custom client."""
    mock_client = MagicMock()
    processor = KGoTProcessor(ollama_client=mock_client)
    assert processor.ollama_client is mock_client
    mock_ollama_client_class.assert_not_called()


def test_identify_decision_points(mock_nodes, mock_edges):
    """Test identify_decision_points method."""
    processor = KGoTProcessor()
    decision_points = processor._identify_decision_points(mock_nodes, mock_edges)
    
    # Check results
    assert len(decision_points) > 0
    
    # ADRs should always be identified as decision points
    adr_node = next(n for n in mock_nodes if n.type == NodeType.ADR)
    assert adr_node in decision_points
    
    # PRs with significant discussion should be identified
    pr_node = next(n for n in mock_nodes if n.type == NodeType.PR)
    assert pr_node in decision_points


@patch("arc_memory.process.kgot.KGoTProcessor._get_decision_context")
def test_generate_reasoning_structure(mock_get_decision_context, mock_ollama_client, mock_nodes, mock_edges):
    """Test generate_reasoning_structure method."""
    # Setup mock
    mock_get_decision_context.return_value = {
        "id": "adr:001",
        "type": "adr",
        "title": "Use SQLite for local storage",
        "body": "We decided to use SQLite for local storage because it's lightweight and doesn't require a separate server.",
        "related_entities": [
            {
                "id": "file:src/storage.py",
                "type": "file",
                "title": "storage.py",
                "relationship": "DECIDES",
                "direction": "outgoing",
            }
        ],
    }
    
    # Create processor with mock client
    processor = KGoTProcessor(ollama_client=mock_ollama_client)
    
    # Get an ADR node as the decision point
    adr_node = next(n for n in mock_nodes if n.type == NodeType.ADR)
    
    # Call the method
    reasoning_nodes, reasoning_edges = processor._generate_reasoning_structure(
        adr_node, mock_nodes, mock_edges
    )
    
    # Check results
    assert len(reasoning_nodes) > 0
    assert len(reasoning_edges) > 0
    
    # Check that the question node was created
    question_node = next(
        (n for n in reasoning_nodes if n.type == NodeType.REASONING_QUESTION), None
    )
    assert question_node is not None
    assert question_node.title == "What database should we use for local storage?"
    
    # Check that alternative nodes were created
    alternative_nodes = [
        n for n in reasoning_nodes if n.type == "reasoning_alternative"
    ]
    assert len(alternative_nodes) == 2
    assert any(n.title == "SQLite" for n in alternative_nodes)
    assert any(n.title == "PostgreSQL" for n in alternative_nodes)
    
    # Check that criterion nodes were created
    criterion_nodes = [
        n for n in reasoning_nodes if n.type == "reasoning_criterion"
    ]
    assert len(criterion_nodes) == 2
    assert any(n.title == "Simplicity" for n in criterion_nodes)
    assert any(n.title == "Performance" for n in criterion_nodes)
    
    # Check that reasoning step nodes were created
    step_nodes = [
        n for n in reasoning_nodes if n.type == "reasoning_step"
    ]
    assert len(step_nodes) == 2
    
    # Check that implication nodes were created
    implication_nodes = [
        n for n in reasoning_nodes if n.type == "reasoning_implication"
    ]
    assert len(implication_nodes) == 2


def test_get_decision_context(mock_nodes, mock_edges):
    """Test get_decision_context method."""
    processor = KGoTProcessor()
    
    # Get an ADR node as the decision point
    adr_node = next(n for n in mock_nodes if n.type == NodeType.ADR)
    
    # Call the method
    context = processor._get_decision_context(adr_node, mock_nodes, mock_edges)
    
    # Check results
    assert context["id"] == adr_node.id
    assert context["type"] == adr_node.type
    assert context["title"] == adr_node.title
    assert context["body"] == adr_node.body
    assert "related_entities" in context
    assert len(context["related_entities"]) > 0


@patch("arc_memory.process.kgot.KGoTProcessor")
def test_enhance_with_reasoning_structures(mock_kgot_processor_class, mock_nodes, mock_edges):
    """Test enhance_with_reasoning_structures function."""
    # Setup mock
    mock_processor = MagicMock()
    mock_processor.process.return_value = (
        [MagicMock(), MagicMock()],  # reasoning_nodes
        [MagicMock(), MagicMock()],  # reasoning_edges
    )
    mock_kgot_processor_class.return_value = mock_processor
    
    # Call the function
    enhanced_nodes, enhanced_edges = enhance_with_reasoning_structures(
        mock_nodes, mock_edges, Path("/fake/repo")
    )
    
    # Check results
    assert len(enhanced_nodes) == len(mock_nodes) + 2
    assert len(enhanced_edges) == len(mock_edges) + 2
    
    # Verify that the processor was called correctly
    mock_processor.process.assert_called_once_with(
        mock_nodes, mock_edges, Path("/fake/repo")
    )
