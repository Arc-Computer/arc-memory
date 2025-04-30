"""Test relationship filtering in the relate command."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from arc_memory.schema.models import Node, NodeType
from arc_memory.cli.relate import get_related_nodes


class TestRelateFiltering(unittest.TestCase):
    """Test relationship filtering in the relate command."""

    @patch("arc_memory.cli.relate.format_trace_results")
    @patch("arc_memory.cli.relate.get_node_by_id")
    @patch("arc_memory.cli.relate.get_connected_nodes")
    def test_get_related_nodes_with_relationship_filter(self, mock_get_connected_nodes, mock_get_node_by_id, mock_format_trace_results):
        """Test filtering related nodes by relationship type."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_entity = MagicMock()

        # Create a proper Node object for the PR
        pr_node = Node(
            id="pr:42",
            type=NodeType.PR,
            title="Test PR",
            body="Test body",
            ts=datetime.now(),
            extra={"number": 42, "state": "open", "url": "https://github.com/test/repo/pull/42"}
        )

        # Mock the entity exists
        mock_get_node_by_id.side_effect = lambda conn, node_id: mock_entity if node_id == "commit:abc123" else pr_node if node_id == "pr:42" else None

        # Mock connected nodes
        mock_get_connected_nodes.return_value = ["pr:42", "issue:123"]

        # Mock cursor for SQL query
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("pr:42",)]  # Only PR:42 has the MERGES relationship

        # Mock format_trace_results to return a list with one formatted node
        formatted_node = {
            "type": "pr",
            "id": "pr:42",
            "title": "Test PR",
            "timestamp": datetime.now().isoformat(),
            "number": 42,
            "state": "open",
            "url": "https://github.com/test/repo/pull/42"
        }
        mock_format_trace_results.return_value = [formatted_node]

        # Call the function with relationship filter
        result = get_related_nodes(mock_conn, "commit:abc123", max_results=10, relationship_type="MERGES")

        # Verify SQL query was executed with correct parameters
        mock_cursor.execute.assert_called_once_with(
            "SELECT dst FROM edges WHERE src = ? AND rel = ? UNION SELECT src FROM edges WHERE dst = ? AND rel = ?",
            ("commit:abc123", "MERGES", "commit:abc123", "MERGES")
        )

        # Verify format_trace_results was called with the correct node
        mock_format_trace_results.assert_called_once()
        args, _ = mock_format_trace_results.call_args
        self.assertEqual(len(args[0]), 1)
        self.assertEqual(args[0][0].id, "pr:42")

        # Verify only nodes with the specified relationship were returned
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "pr:42")


if __name__ == "__main__":
    unittest.main()
