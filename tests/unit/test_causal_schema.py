"""Unit tests for the causal relationship schema models."""

from datetime import datetime
import pytest

from arc_memory.schema.models import (
    Node,
    Edge,
    NodeType,
    EdgeRel,
    DecisionNode,
    ImplicationNode,
    CodeChangeNode,
)


def test_decision_node_creation():
    """Test creating a DecisionNode."""
    # Create a decision node
    decision = DecisionNode(
        id="decision:123",
        title="Use SQLite for local storage",
        body="We decided to use SQLite for local storage because it's lightweight.",
        decision_type="architectural",
        decision_makers=["John Doe", "Jane Smith"],
        alternatives=[
            {"name": "PostgreSQL", "description": "Full-featured SQL database"},
            {"name": "MongoDB", "description": "NoSQL document database"},
        ],
        criteria=[
            {"name": "Performance", "description": "Database performance"},
            {"name": "Simplicity", "description": "Ease of setup and use"},
        ],
        confidence=0.9,
        source="adr:001",
    )

    # Check the node properties
    assert decision.id == "decision:123"
    assert decision.type == NodeType.DECISION
    assert decision.title == "Use SQLite for local storage"
    assert decision.body == "We decided to use SQLite for local storage because it's lightweight."
    assert decision.decision_type == "architectural"
    assert len(decision.decision_makers) == 2
    assert "John Doe" in decision.decision_makers
    assert len(decision.alternatives) == 2
    assert decision.alternatives[0]["name"] == "PostgreSQL"
    assert len(decision.criteria) == 2
    assert decision.criteria[1]["name"] == "Simplicity"
    assert decision.confidence == 0.9
    assert decision.source == "adr:001"


def test_implication_node_creation():
    """Test creating an ImplicationNode."""
    # Create an implication node
    implication = ImplicationNode(
        id="implication:456",
        title="Limited concurrent connections",
        body="Using SQLite limits the number of concurrent connections.",
        implication_type="technical",
        severity="medium",
        scope=["src/db/connection.py", "src/api/endpoints.py"],
        confidence=0.8,
        source="decision:123",
    )

    # Check the node properties
    assert implication.id == "implication:456"
    assert implication.type == NodeType.IMPLICATION
    assert implication.title == "Limited concurrent connections"
    assert implication.body == "Using SQLite limits the number of concurrent connections."
    assert implication.implication_type == "technical"
    assert implication.severity == "medium"
    assert len(implication.scope) == 2
    assert "src/db/connection.py" in implication.scope
    assert implication.confidence == 0.8
    assert implication.source == "decision:123"


def test_code_change_node_creation():
    """Test creating a CodeChangeNode."""
    # Create a code change node
    code_change = CodeChangeNode(
        id="code_change:789",
        title="Implement connection pooling",
        body="Added connection pooling to mitigate SQLite connection limits.",
        change_type="feature",
        files=["src/db/connection_pool.py", "src/db/connection.py"],
        description="Implemented a connection pool to manage SQLite connections.",
        author="John Doe",
        commit_sha="abc123",
        confidence=0.95,
    )

    # Check the node properties
    assert code_change.id == "code_change:789"
    assert code_change.type == NodeType.CODE_CHANGE
    assert code_change.title == "Implement connection pooling"
    assert code_change.body == "Added connection pooling to mitigate SQLite connection limits."
    assert code_change.change_type == "feature"
    assert len(code_change.files) == 2
    assert "src/db/connection_pool.py" in code_change.files
    assert code_change.description == "Implemented a connection pool to manage SQLite connections."
    assert code_change.author == "John Doe"
    assert code_change.commit_sha == "abc123"
    assert code_change.confidence == 0.95


def test_causal_edge_creation():
    """Test creating edges for causal relationships."""
    # Create nodes
    decision = DecisionNode(
        id="decision:123",
        title="Use SQLite for local storage",
        decision_type="architectural",
    )
    
    implication = ImplicationNode(
        id="implication:456",
        title="Limited concurrent connections",
        implication_type="technical",
    )
    
    code_change = CodeChangeNode(
        id="code_change:789",
        title="Implement connection pooling",
        change_type="feature",
        description="Implemented a connection pool to manage SQLite connections.",
    )
    
    # Create edges
    decision_to_implication = Edge(
        src=decision.id,
        dst=implication.id,
        rel=EdgeRel.LEADS_TO,
        properties={"confidence": 0.9},
    )
    
    implication_to_code_change = Edge(
        src=implication.id,
        dst=code_change.id,
        rel=EdgeRel.RESULTS_IN,
        properties={"confidence": 0.8},
    )
    
    code_change_to_decision = Edge(
        src=code_change.id,
        dst=decision.id,
        rel=EdgeRel.IMPLEMENTS_DECISION,
        properties={"confidence": 0.95},
    )
    
    # Check edge properties
    assert decision_to_implication.src == "decision:123"
    assert decision_to_implication.dst == "implication:456"
    assert decision_to_implication.rel == EdgeRel.LEADS_TO
    assert decision_to_implication.properties["confidence"] == 0.9
    
    assert implication_to_code_change.src == "implication:456"
    assert implication_to_code_change.dst == "code_change:789"
    assert implication_to_code_change.rel == EdgeRel.RESULTS_IN
    assert implication_to_code_change.properties["confidence"] == 0.8
    
    assert code_change_to_decision.src == "code_change:789"
    assert code_change_to_decision.dst == "decision:123"
    assert code_change_to_decision.rel == EdgeRel.IMPLEMENTS_DECISION
    assert code_change_to_decision.properties["confidence"] == 0.95
