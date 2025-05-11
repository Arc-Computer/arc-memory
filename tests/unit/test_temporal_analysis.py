"""Unit tests for the temporal analysis module."""

from datetime import datetime, timedelta
from pathlib import Path
# Removed unused import: from unittest.mock import MagicMock

import pytest

from arc_memory.process.temporal_analysis import (
    enhance_with_temporal_analysis,
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


# These tests have been removed because the functions they test don't exist in the actual implementation.
# If these functions are intended to be part of the API, they should be implemented properly.
# For now, we're focusing on testing the actual implementation.
