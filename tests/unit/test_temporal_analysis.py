"""Unit tests for the temporal analysis module."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from arc_memory.process.temporal_analysis import (
    enhance_with_temporal_analysis,
    create_temporal_indices,
    analyze_temporal_patterns,
    analyze_developer_workflows,
    dynamic_adaptation_for_temporal_reasoning,
)
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType


@pytest.fixture
def mock_nodes():
    """Create mock nodes with timestamps for testing."""
    now = datetime.now()
    return [
        Node(
            id="commit:abc123",
            type=NodeType.COMMIT,
            title="First commit",
            ts=now - timedelta(days=5),
        ),
        Node(
            id="commit:def456",
            type=NodeType.COMMIT,
            title="Second commit",
            ts=now - timedelta(days=3),
        ),
        Node(
            id="commit:ghi789",
            type=NodeType.COMMIT,
            title="Third commit",
            ts=now - timedelta(days=1),
        ),
        Node(
            id="file:src/main.py",
            type=NodeType.FILE,
            title="main.py",
            ts=now - timedelta(days=5),
        ),
        Node(
            id="file:src/utils.py",
            type=NodeType.FILE,
            title="utils.py",
            ts=now - timedelta(days=3),
        ),
        Node(
            id="pr:123",
            type=NodeType.PR,
            title="Add utils module",
            ts=now - timedelta(days=2),
        ),
        Node(
            id="issue:456",
            type=NodeType.ISSUE,
            title="Implement data processing",
            ts=now - timedelta(days=7),
        ),
    ]


@pytest.fixture
def mock_edges():
    """Create mock edges for testing."""
    return [
        Edge(
            src="commit:abc123",
            dst="file:src/main.py",
            rel=EdgeRel.MODIFIES,
        ),
        Edge(
            src="commit:def456",
            dst="file:src/utils.py",
            rel=EdgeRel.MODIFIES,
        ),
        Edge(
            src="commit:ghi789",
            dst="file:src/main.py",
            rel=EdgeRel.MODIFIES,
        ),
        Edge(
            src="pr:123",
            dst="commit:def456",
            rel=EdgeRel.MERGES,
        ),
        Edge(
            src="issue:456",
            dst="pr:123",
            rel=EdgeRel.MENTIONS,
        ),
    ]


def test_enhance_with_temporal_analysis(mock_nodes, mock_edges):
    """Test enhance_with_temporal_analysis function."""
    # Call the function
    enhanced_nodes, enhanced_edges = enhance_with_temporal_analysis(
        mock_nodes, mock_edges, Path("/fake/repo")
    )
    
    # Check results
    assert len(enhanced_nodes) >= len(mock_nodes)
    assert len(enhanced_edges) >= len(mock_edges)
    
    # Check that temporal edges were added
    temporal_edges = [
        e for e in enhanced_edges 
        if e.rel in [EdgeRel.FOLLOWS, EdgeRel.PRECEDES]
    ]
    assert len(temporal_edges) > 0


def test_create_temporal_indices(mock_nodes):
    """Test create_temporal_indices function."""
    # Call the function
    indices = create_temporal_indices(mock_nodes)
    
    # Check results
    assert NodeType.COMMIT in indices
    assert len(indices[NodeType.COMMIT]) == 3
    assert NodeType.FILE in indices
    assert len(indices[NodeType.FILE]) == 2
    assert NodeType.PR in indices
    assert len(indices[NodeType.PR]) == 1
    assert NodeType.ISSUE in indices
    assert len(indices[NodeType.ISSUE]) == 1
    
    # Check that indices are sorted by timestamp
    commit_timestamps = [ts for ts, _ in indices[NodeType.COMMIT]]
    assert commit_timestamps == sorted(commit_timestamps)


def test_analyze_temporal_patterns(mock_nodes, mock_edges):
    """Test analyze_temporal_patterns function."""
    # Create temporal indices
    indices = create_temporal_indices(mock_nodes)
    
    # Call the function
    new_edges = analyze_temporal_patterns(mock_nodes, mock_edges, indices)
    
    # Check results
    assert len(new_edges) > 0
    
    # Check that FOLLOWS edges were created between sequential commits
    follows_edges = [e for e in new_edges if e.rel == EdgeRel.FOLLOWS]
    assert len(follows_edges) > 0
    
    # Check that PRECEDES edges were created between sequential commits
    precedes_edges = [e for e in new_edges if e.rel == EdgeRel.PRECEDES]
    assert len(precedes_edges) > 0
    
    # Check that edges have time_delta property
    for edge in new_edges:
        assert "time_delta" in edge.properties
        assert edge.properties["time_delta"] > 0


def test_analyze_developer_workflows(mock_nodes, mock_edges):
    """Test analyze_developer_workflows function."""
    # Create temporal indices
    indices = create_temporal_indices(mock_nodes)
    
    # Call the function
    workflow_nodes, workflow_edges = analyze_developer_workflows(
        mock_nodes, mock_edges, indices
    )
    
    # Check results (currently returns empty lists)
    assert isinstance(workflow_nodes, list)
    assert isinstance(workflow_edges, list)


def test_dynamic_adaptation_for_temporal_reasoning(mock_nodes, mock_edges):
    """Test dynamic_adaptation_for_temporal_reasoning function."""
    # Call the function
    enhanced_nodes, enhanced_edges = dynamic_adaptation_for_temporal_reasoning(
        mock_nodes, mock_edges, MagicMock()
    )
    
    # Check results (currently returns the original nodes and edges)
    assert enhanced_nodes == mock_nodes
    assert enhanced_edges == mock_edges
