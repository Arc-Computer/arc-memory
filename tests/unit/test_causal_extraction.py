"""Unit tests for the causal relationship extraction module."""

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
from arc_memory.process.causal_extraction import (
    extract_causal_relationships,
    extract_causal_relationships_rule_based,
    extract_from_commits,
    extract_from_prs,
    extract_from_issues,
    extract_from_adrs,
    connect_causal_nodes,
)


def test_extract_from_commits():
    """Test extracting causal relationships from commit messages."""
    # Create test commit nodes
    commit1 = CommitNode(
        id="commit:123",
        type=NodeType.COMMIT,
        title="Implement SQLite connection pooling",
        body="Decided to implement connection pooling to mitigate SQLite connection limits.",
        ts=datetime.now(),
        sha="abc123",
        author="John Doe",
        files=["src/db/connection_pool.py", "src/db/connection.py"],
    )

    commit2 = CommitNode(
        id="commit:456",
        type=NodeType.COMMIT,
        title="Fix bug in authentication",
        body="Fixed a bug in the authentication flow that was causing login failures.",
        ts=datetime.now(),
        sha="def456",
        author="Jane Smith",
        files=["src/auth/login.py"],
    )

    # Test extraction
    nodes, edges = extract_from_commits([commit1, commit2], [])

    # Check results for commit1 (should extract decision and code change)
    assert len(nodes) >= 2
    assert len(edges) >= 2

    # Find decision node
    decision_nodes = [n for n in nodes if n.type == NodeType.DECISION]
    assert len(decision_nodes) >= 1
    decision = decision_nodes[0]
    assert decision.title.startswith("Decision from commit")
    assert "connection pooling" in decision.body.lower()

    # Find code change node
    code_change_nodes = [n for n in nodes if n.type == NodeType.CODE_CHANGE]
    assert len(code_change_nodes) >= 1
    code_change = code_change_nodes[0]
    assert code_change.title.startswith("Code changes from commit")
    assert len(code_change.files) == 2
    assert "src/db/connection_pool.py" in code_change.files

    # Check edges
    decision_edges = [e for e in edges if e.rel == EdgeRel.IMPLEMENTS_DECISION]
    assert len(decision_edges) >= 1
    assert decision_edges[0].src == "commit:123"
    assert decision_edges[0].dst == decision.id


def test_extract_from_prs():
    """Test extracting causal relationships from PR descriptions."""
    # Create test PR nodes
    pr1 = PRNode(
        id="pr:123",
        type=NodeType.PR,
        title="Add SQLite connection pooling",
        body="""
        ## Why
        SQLite has limitations on concurrent connections, which was causing issues in our API.

        ## Solution
        Implemented a connection pool to manage SQLite connections efficiently.

        ## Impact
        This change will improve performance and stability under high load.
        """,
        ts=datetime.now(),
        number=123,
        merged_by="John Doe",
        state="merged",
        url="https://github.com/example/repo/pull/123",
    )

    # Test extraction
    nodes, edges = extract_from_prs([pr1], [])

    # Check results
    assert len(nodes) >= 2
    assert len(edges) >= 2

    # Find decision node
    decision_nodes = [n for n in nodes if n.type == NodeType.DECISION]
    assert len(decision_nodes) >= 1
    decision = decision_nodes[0]
    assert decision.title.startswith("Decision from PR")

    # Find implication node
    implication_nodes = [n for n in nodes if n.type == NodeType.IMPLICATION]
    assert len(implication_nodes) >= 1
    implication = implication_nodes[0]
    assert implication.title.startswith("Implication from PR")

    # Check edges
    decision_edges = [e for e in edges if e.rel == EdgeRel.IMPLEMENTS_DECISION]
    assert len(decision_edges) >= 1
    assert decision_edges[0].src == "pr:123"

    implication_edges = [e for e in edges if e.rel == EdgeRel.CAUSED_BY]
    assert len(implication_edges) >= 1
    assert implication_edges[0].src == "pr:123"


def test_extract_from_issues():
    """Test extracting causal relationships from issues (Linear tickets)."""
    # Create test issue nodes
    issue1 = IssueNode(
        id="issue:123",
        type=NodeType.ISSUE,
        title="Implement connection pooling for SQLite",
        body="""
        We need to implement connection pooling for SQLite because we're hitting connection limits under load.

        This will impact the database layer and API performance.
        """,
        ts=datetime.now(),
        number=123,
        status="Done",
        state="completed",
        url="https://linear.app/example/issue/123",
    )

    # Test extraction
    nodes, edges = extract_from_issues([issue1], [])

    # Check results
    assert len(nodes) >= 2
    assert len(edges) >= 2

    # Find decision node
    decision_nodes = [n for n in nodes if n.type == NodeType.DECISION]
    assert len(decision_nodes) >= 1
    decision = decision_nodes[0]
    assert decision.title.startswith("Decision from issue")
    assert decision.decision_type == "requirement"

    # Find implication node
    implication_nodes = [n for n in nodes if n.type == NodeType.IMPLICATION]
    assert len(implication_nodes) >= 1
    implication = implication_nodes[0]
    assert implication.title.startswith("Implication from issue")
    assert implication.implication_type == "business"

    # Check edges
    decision_edges = [e for e in edges if e.rel == EdgeRel.ADDRESSES]
    assert len(decision_edges) >= 1
    assert decision_edges[0].src == "issue:123"

    implication_edges = [e for e in edges if e.rel == EdgeRel.LEADS_TO]
    assert len(implication_edges) >= 1
    assert implication_edges[0].src == "issue:123"


def test_extract_from_adrs():
    """Test extracting causal relationships from ADRs."""
    # Create test ADR nodes
    adr1 = ADRNode(
        id="adr:123",
        type=NodeType.ADR,
        title="Use SQLite for local storage",
        body="""
        # ADR 1: Use SQLite for local storage

        ## Context
        We need a local storage solution for our application.

        ## Decision
        We will use SQLite for local storage because it's lightweight and doesn't require a separate server.

        ## Consequences
        - Limited concurrent connections
        - Simpler deployment
        - Lower resource usage
        """,
        ts=datetime.now(),
        number=1,
        status="Accepted",
        path="docs/adrs/adr-001.md",
    )

    # Test extraction
    nodes, edges = extract_from_adrs([adr1], [])

    # Check results
    assert len(nodes) >= 2
    assert len(edges) >= 2

    # Find decision node
    decision_nodes = [n for n in nodes if n.type == NodeType.DECISION]
    assert len(decision_nodes) >= 1
    decision = decision_nodes[0]
    assert decision.title.startswith("Decision from ADR")
    assert decision.decision_type == "architectural"

    # Find implication node
    implication_nodes = [n for n in nodes if n.type == NodeType.IMPLICATION]
    assert len(implication_nodes) >= 1
    implication = implication_nodes[0]
    assert implication.title.startswith("Implication from ADR")
    assert implication.implication_type == "architectural"
    assert implication.severity == "high"

    # Check edges
    decision_edges = [e for e in edges if e.rel == EdgeRel.DECIDES]
    assert len(decision_edges) >= 1
    assert decision_edges[0].src == "adr:123"

    implication_edges = [e for e in edges if e.rel == EdgeRel.LEADS_TO]
    assert len(implication_edges) >= 1
    assert implication_edges[0].src == decision.id
    assert implication_edges[0].dst == implication.id


def test_connect_causal_nodes():
    """Test connecting related causal nodes."""
    # Create test nodes
    decision1 = DecisionNode(
        id="decision:123",
        type=NodeType.DECISION,
        title="Use SQLite",
        source="commit:123",
        decision_type="architectural",
    )

    implication1 = ImplicationNode(
        id="implication:456",
        type=NodeType.IMPLICATION,
        title="Limited connections",
        source="pr:456",
        implication_type="technical",
        severity="medium",
    )

    code_change1 = CodeChangeNode(
        id="code_change:789",
        type=NodeType.CODE_CHANGE,
        title="Implement connection pooling",
        source="commit:789",
        change_type="feature",
        description="Implemented connection pooling",
    )

    # Create original nodes and edges
    commit1 = CommitNode(id="commit:123", type=NodeType.COMMIT, title="Commit 1", author="John Doe", files=["file1.py"], sha="abc123")
    pr1 = PRNode(id="pr:456", type=NodeType.PR, title="PR 1", state="merged", url="https://github.com/example/repo/pull/456", number=456)
    commit2 = CommitNode(id="commit:789", type=NodeType.COMMIT, title="Commit 2", author="Jane Smith", files=["file2.py"], sha="def456")

    # Create MENTIONS edges
    edge1 = Edge(src="commit:123", dst="pr:456", rel=EdgeRel.MENTIONS)
    edge2 = Edge(src="pr:456", dst="commit:789", rel=EdgeRel.MENTIONS)

    # Test connection
    edges = connect_causal_nodes(
        [decision1, implication1, code_change1],
        [commit1, pr1, commit2],
        [edge1, edge2],
    )

    # Check results
    assert len(edges) >= 1

    # Check for decision -> implication edge
    decision_implication_edges = [
        e for e in edges if e.src == "decision:123" and e.dst == "implication:456"
    ]
    assert len(decision_implication_edges) >= 1
    assert decision_implication_edges[0].rel == EdgeRel.LEADS_TO


def test_extract_causal_relationships_rule_based():
    """Test the rule-based causal relationship extraction."""
    # Create test nodes
    commit = CommitNode(
        id="commit:123",
        type=NodeType.COMMIT,
        title="Implement SQLite connection pooling",
        body="Decided to implement connection pooling to mitigate SQLite connection limits.",
        ts=datetime.now(),
        sha="abc123",
        author="John Doe",
        files=["src/db/connection_pool.py", "src/db/connection.py"],
    )

    pr = PRNode(
        id="pr:456",
        type=NodeType.PR,
        title="Add SQLite connection pooling",
        body="""
        ## Why
        SQLite has limitations on concurrent connections, which was causing issues in our API.

        ## Solution
        Implemented a connection pool to manage SQLite connections efficiently.
        """,
        ts=datetime.now(),
        number=456,
        merged_by="John Doe",
        state="merged",
        url="https://github.com/example/repo/pull/456",
    )

    # Create MENTIONS edge
    edge = Edge(src="commit:123", dst="pr:456", rel=EdgeRel.MENTIONS)

    # Test extraction
    nodes, edges = extract_causal_relationships_rule_based([commit, pr], [edge])

    # Check results
    assert len(nodes) >= 3  # At least decision, implication, and code change
    assert len(edges) >= 3  # At least 3 edges

    # Check node types
    node_types = [n.type for n in nodes]
    assert NodeType.DECISION in node_types
    assert NodeType.CODE_CHANGE in node_types

    # Check edge types
    edge_rels = [e.rel for e in edges]
    assert EdgeRel.IMPLEMENTS_DECISION in edge_rels
    assert EdgeRel.RESULTS_IN in edge_rels


@patch("arc_memory.process.causal_extraction.extract_causal_relationships_rule_based")
@patch("arc_memory.process.causal_extraction.extract_causal_relationships_llm")
def test_extract_causal_relationships(mock_llm, mock_rule_based):
    """Test the main causal relationship extraction function."""
    # Set up mocks
    mock_rule_based.return_value = (
        [DecisionNode(id="decision:123", type=NodeType.DECISION, title="Rule-based decision", decision_type="implementation")],
        [Edge(src="commit:123", dst="decision:123", rel=EdgeRel.IMPLEMENTS_DECISION)],
    )

    mock_llm.return_value = (
        [ImplicationNode(id="implication:456", type=NodeType.IMPLICATION, title="LLM implication", implication_type="technical", severity="medium")],
        [Edge(src="decision:123", dst="implication:456", rel=EdgeRel.LEADS_TO)],
    )

    # Create test nodes and edges
    nodes = [
        CommitNode(id="commit:123", type=NodeType.COMMIT, title="Test commit", author="John Doe", files=["file1.py"], sha="abc123"),
        PRNode(id="pr:456", type=NodeType.PR, title="Test PR", state="merged", url="https://github.com/example/repo/pull/456", number=456),
    ]
    edges = [Edge(src="commit:123", dst="pr:456", rel=EdgeRel.MENTIONS)]

    # Test with standard enhancement level
    result_nodes, result_edges = extract_causal_relationships(
        nodes, edges, enhancement_level="standard"
    )

    # Check results
    assert len(result_nodes) == 2  # 1 from rule-based + 1 from LLM
    assert len(result_edges) == 2  # 1 from rule-based + 1 from LLM

    # Verify mock calls
    mock_rule_based.assert_called_once_with(nodes, edges)
    mock_llm.assert_called_once()

    # Test with fast enhancement level
    mock_rule_based.reset_mock()
    mock_llm.reset_mock()

    result_nodes, result_edges = extract_causal_relationships(
        nodes, edges, enhancement_level="fast"
    )

    # Check results
    assert len(result_nodes) == 1  # Only from rule-based
    assert len(result_edges) == 1  # Only from rule-based

    # Verify mock calls
    mock_rule_based.assert_called_once_with(nodes, edges)
    mock_llm.assert_not_called()
