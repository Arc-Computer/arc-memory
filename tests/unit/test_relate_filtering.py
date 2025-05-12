"""Test relationship filtering in the SDK relationships module."""

import unittest
from unittest.mock import MagicMock
from datetime import datetime

from arc_memory.schema.models import NodeType, EdgeRel


class TestRelateFiltering(unittest.TestCase):
    """Test relationship filtering in the SDK relationships module."""

    def test_get_related_entities_with_relationship_filter(self):
        """Test filtering related entities by relationship type."""
        # Import the function
        from arc_memory.sdk.relationships import get_related_entities

        # Create a mock adapter
        mock_adapter = MagicMock()

        # Setup mock return values

        # Mock outgoing edges
        mock_adapter.get_edges_by_src.return_value = [
            {
                "src": "commit:abc123",
                "dst": "pr:42",
                "rel": "MERGES",
                "properties": {}
            }
        ]

        # Mock incoming edges (empty)
        mock_adapter.get_edges_by_dst.return_value = []

        # Mock PR node
        pr_node = {
            "id": "pr:42",
            "type": NodeType.PR,
            "title": "Test PR",
            "body": "Test body",
            "timestamp": datetime.now().isoformat(),
            "extra": {
                "number": 42,
                "state": "open",
                "url": "https://github.com/test/repo/pull/42"
            }
        }
        mock_adapter.get_node_by_id.return_value = pr_node

        # Call the function with relationship filter
        result = get_related_entities(
            adapter=mock_adapter,
            entity_id="commit:abc123",
            relationship_types=["MERGES"],
            direction="both",
            max_results=10,
            include_properties=True
        )

        # Verify the adapter methods were called with the correct parameters
        mock_adapter.get_edges_by_src.assert_called_once_with("commit:abc123")
        mock_adapter.get_edges_by_dst.assert_called_once_with("commit:abc123")
        mock_adapter.get_node_by_id.assert_called_once_with("pr:42")

        # Verify only entities with the specified relationship were returned
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "pr:42")
        self.assertEqual(result[0].type, NodeType.PR)
        self.assertEqual(result[0].title, "Test PR")
        self.assertEqual(result[0].relationship, EdgeRel.MERGES)
        self.assertEqual(result[0].direction, "outgoing")


if __name__ == "__main__":
    unittest.main()
