"""Test relationship filtering in the relate command."""

import unittest
from unittest.mock import patch, MagicMock

from arc_memory.cli.relate import get_related_nodes


class TestRelateFiltering(unittest.TestCase):
    """Test relationship filtering in the relate command."""

    @patch("arc_memory.cli.relate.get_node_by_id")
    @patch("arc_memory.cli.relate.get_connected_nodes")
    def test_get_related_nodes_with_relationship_filter(self, mock_get_connected_nodes, mock_get_node_by_id):
        """Test filtering related nodes by relationship type."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_entity = MagicMock()
        mock_node_by_id = MagicMock()
        
        # Mock the entity exists
        mock_get_node_by_id.side_effect = lambda conn, node_id: mock_entity if node_id == "commit:abc123" else mock_node_by_id
        
        # Mock connected nodes
        mock_get_connected_nodes.return_value = ["pr:42", "issue:123"]
        
        # Mock cursor for SQL query
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("pr:42",)]  # Only PR:42 has the MERGES relationship
        
        # Mock node details
        mock_node_by_id.id = "pr:42"
        mock_node_by_id.type = "pr"
        mock_node_by_id.title = "Test PR"
        mock_node_by_id.ts = None
        mock_node_by_id.extra = {"number": 42, "state": "open", "url": "https://github.com/test/repo/pull/42"}
        
        # Call the function with relationship filter
        result = get_related_nodes(mock_conn, "commit:abc123", max_results=10, relationship_type="MERGES")
        
        # Verify SQL query was executed with correct parameters
        mock_cursor.execute.assert_called_once_with(
            "SELECT dst FROM edges WHERE src = ? AND rel = ? UNION SELECT src FROM edges WHERE dst = ? AND rel = ?",
            ("commit:abc123", "MERGES", "commit:abc123", "MERGES")
        )
        
        # Verify only nodes with the specified relationship were returned
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "pr:42")


if __name__ == "__main__":
    unittest.main()
