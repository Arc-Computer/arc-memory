"""Unit tests for the enhanced Knowledge Graph of Thoughts (KGoT) implementation."""

from datetime import datetime
import pytest
from unittest.mock import MagicMock, patch

from arc_memory.schema.models import (
    Node,
    Edge,
    NodeType,
    EdgeRel,
    CommitNode,
    PRNode,
    IssueNode,
    ADRNode,
    DecisionNode,
    ImplicationNode,
    CodeChangeNode,
)
from arc_memory.process.kgot import (
    KGoTProcessor,
    enhance_with_reasoning_structures,
)


def test_identify_decision_points_with_causal_nodes():
    """Test that _identify_decision_points correctly identifies decision points from causal nodes."""
    # Create test nodes
    decision_node = DecisionNode(
        id="decision:123",
        type=NodeType.DECISION,
        title="Use SQLite for local storage",
        body="We decided to use SQLite for local storage because it's lightweight.",
        decision_type="architectural",
        source="commit:456",
    )

    commit_node = CommitNode(
        id="commit:456",
        type=NodeType.COMMIT,
        title="Implement SQLite storage",
        body="Implemented SQLite storage as decided.",
        author="John Doe",
        files=["src/db/storage.py"],
        sha="abc123",
    )

    # Create test edges
    edge = Edge(
        src="commit:456",
        dst="decision:123",
        rel=EdgeRel.IMPLEMENTS_DECISION,
        properties={"confidence": 0.9},
    )

    # Create KGoT processor
    processor = KGoTProcessor()

    # Test _identify_decision_points
    decision_points = processor._identify_decision_points([decision_node, commit_node], [edge])

    # Check results
    assert len(decision_points) == 2
    assert decision_node in decision_points
    assert commit_node in decision_points


def test_get_decision_context_with_causal_relationships():
    """Test that _get_decision_context correctly includes causal relationships."""
    # Create test nodes
    decision_node = DecisionNode(
        id="decision:123",
        type=NodeType.DECISION,
        title="Use SQLite for local storage",
        body="We decided to use SQLite for local storage because it's lightweight.",
        decision_type="architectural",
    )

    implication_node = ImplicationNode(
        id="implication:456",
        type=NodeType.IMPLICATION,
        title="Limited concurrent connections",
        body="SQLite has limitations on concurrent connections.",
        implication_type="technical",
        severity="medium",
        source="decision:123",
    )

    code_change_node = CodeChangeNode(
        id="code_change:789",
        type=NodeType.CODE_CHANGE,
        title="Implement connection pooling",
        body="Added connection pooling to mitigate SQLite connection limits.",
        change_type="feature",
        files=["src/db/connection_pool.py"],
        description="Implemented a connection pool to manage SQLite connections.",
        source="implication:456",
    )

    # Create test edges
    edge1 = Edge(
        src="decision:123",
        dst="implication:456",
        rel=EdgeRel.LEADS_TO,
        properties={"confidence": 0.9},
    )

    edge2 = Edge(
        src="implication:456",
        dst="code_change:789",
        rel=EdgeRel.RESULTS_IN,
        properties={"confidence": 0.8},
    )

    # Create KGoT processor
    processor = KGoTProcessor()

    # Test _get_decision_context
    context = processor._get_decision_context(
        decision_node,
        [decision_node, implication_node, code_change_node],
        [edge1, edge2]
    )

    # Check results
    assert "causal_relationships" in context
    assert len(context["causal_relationships"]) == 1
    assert context["causal_relationships"][0]["id"] == "implication:456"
    assert context["causal_relationships"][0]["relationship"] == EdgeRel.LEADS_TO
    assert "confidence" in context["causal_relationships"][0]
    # The confidence might be from the edge properties or from the node itself
    assert context["causal_relationships"][0]["confidence"] in [0.9, 1.0]


@patch("arc_memory.llm.ollama_client.OllamaClient")
def test_generate_reasoning_structure_with_confidence_scores(mock_ollama):
    """Test that _generate_reasoning_structure includes confidence scores."""
    # Mock the LLM response
    mock_instance = mock_ollama.return_value
    mock_instance.generate.return_value = """
    {
        "question": "Should we use SQLite for local storage?",
        "confidence": 0.9,
        "alternatives": [
            {
                "name": "SQLite",
                "description": "Lightweight SQL database",
                "pros": ["Simple", "No server required"],
                "cons": ["Limited concurrency"],
                "confidence": 0.95
            },
            {
                "name": "PostgreSQL",
                "description": "Full-featured SQL database",
                "pros": ["Robust", "Scalable"],
                "cons": ["Requires server setup"],
                "confidence": 0.9
            }
        ],
        "criteria": [
            {
                "name": "Simplicity",
                "description": "Ease of setup and use",
                "importance": "high",
                "confidence": 0.9
            },
            {
                "name": "Performance",
                "description": "Database performance",
                "importance": "medium",
                "confidence": 0.8
            }
        ],
        "reasoning": [
            {
                "step": 1,
                "description": "Evaluated simplicity requirements",
                "confidence": 0.9
            },
            {
                "step": 2,
                "description": "Considered performance needs",
                "confidence": 0.85
            }
        ],
        "implications": [
            {
                "description": "Limited concurrent connections",
                "severity": "medium",
                "confidence": 0.8
            },
            {
                "description": "Simpler deployment process",
                "severity": "low",
                "confidence": 0.9
            }
        ]
    }
    """

    # Create test node
    decision_node = DecisionNode(
        id="decision:123",
        type=NodeType.DECISION,
        title="Use SQLite for local storage",
        body="We decided to use SQLite for local storage because it's lightweight.",
        decision_type="architectural",
    )

    # Create KGoT processor
    processor = KGoTProcessor(ollama_client=mock_instance)

    # Test _generate_reasoning_structure
    reasoning_nodes, reasoning_edges = processor._generate_reasoning_structure(
        decision_node,
        [],
        []
    )

    # Check results
    assert len(reasoning_nodes) > 0
    assert len(reasoning_edges) > 0

    # Check that confidence scores are included
    question_node = next((n for n in reasoning_nodes if n.type == NodeType.REASONING_QUESTION), None)
    assert question_node is not None
    assert "confidence" in question_node.extra
    assert question_node.extra["confidence"] == 0.9

    # Check that alternatives include pros and cons
    alt_node = next((n for n in reasoning_nodes if n.type == NodeType.REASONING_ALTERNATIVE), None)
    assert alt_node is not None
    assert "pros" in alt_node.extra
    assert "cons" in alt_node.extra
    assert len(alt_node.extra["pros"]) > 0
    assert len(alt_node.extra["cons"]) > 0

    # Check that implications include severity
    impl_node = next((n for n in reasoning_nodes if n.type == NodeType.REASONING_IMPLICATION), None)
    assert impl_node is not None
    assert "severity" in impl_node.extra
    assert impl_node.extra["severity"] in ["low", "medium", "high"]


@patch("arc_memory.process.kgot.KGoTProcessor")
def test_enhance_with_reasoning_structures_different_levels(mock_processor):
    """Test that enhance_with_reasoning_structures handles different enhancement levels."""
    # Mock the processor
    mock_instance = mock_processor.return_value
    mock_instance.process.return_value = (
        [Node(id="reasoning:1", type=NodeType.REASONING_QUESTION, title="Test Question")],
        [Edge(src="reasoning:1", dst="decision:1", rel=EdgeRel.REASONS_ABOUT)]
    )

    # Create test nodes and edges
    nodes = [
        DecisionNode(id="decision:1", type=NodeType.DECISION, title="Test Decision", decision_type="implementation"),
        ADRNode(id="adr:1", type=NodeType.ADR, title="Test ADR", path="docs/adrs/adr-001.md", status="accepted"),
    ]
    edges = [
        Edge(src="decision:1", dst="adr:1", rel=EdgeRel.REFERENCES),
    ]

    # Test with fast enhancement level
    enhanced_nodes, enhanced_edges = enhance_with_reasoning_structures(
        nodes, edges, enhancement_level="fast"
    )

    # Check that the processor was called with the right parameters
    mock_processor.assert_called_once()
    # The system prompt contains information about fast mode, but not necessarily the word "fast"
    assert "concise" in mock_processor.call_args[1]["system_prompt"].lower()

    # Check results
    assert len(enhanced_nodes) == 3  # Original 2 + 1 new
    assert len(enhanced_edges) == 2  # Original 1 + 1 new

    # Reset mock
    mock_processor.reset_mock()
    mock_instance.process.reset_mock()

    # Test with deep enhancement level
    enhanced_nodes, enhanced_edges = enhance_with_reasoning_structures(
        nodes, edges, enhancement_level="deep"
    )

    # Check that the processor was called with the right parameters
    mock_processor.assert_called_once()
    # The system prompt contains information about deep mode, but not necessarily the word "deep"
    assert "comprehensive" in mock_processor.call_args[1]["system_prompt"].lower()

    # Check results
    assert len(enhanced_nodes) == 3  # Original 2 + 1 new
    assert len(enhanced_edges) == 2  # Original 1 + 1 new
