"""Tests for the relate command."""

import json
import unittest
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from arc_memory.cli import app

runner = CliRunner()


class TestRelateCommand(unittest.TestCase):
    """Tests for the relate command."""

    @patch("arc_memory.cli.relate.get_related_nodes")
    @patch("arc_memory.sql.db.get_connection")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_relate_node_text_format(self, mock_exists, mock_ensure_arc_dir, mock_get_connection, mock_get_related_nodes):
        """Test the relate node command with text format."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_get_connection.return_value = MagicMock()
        mock_get_related_nodes.return_value = [
            {
                "type": "pr",
                "id": "pr:42",
                "title": "Add login feature",
                "timestamp": "2023-01-01T12:00:00",
                "number": 42,
                "state": "merged",
                "url": "https://github.com/org/repo/pull/42"
            }
        ]

        # Run command
        result = runner.invoke(app, ["relate", "node", "commit:abc123"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Add login feature", result.stdout)
        self.assertIn("PR #42", result.stdout)
        self.assertIn("merged", result.stdout)

    @patch("arc_memory.cli.relate.get_related_nodes")
    @patch("arc_memory.sql.db.get_connection")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_relate_node_json_format(self, mock_exists, mock_ensure_arc_dir, mock_get_connection, mock_get_related_nodes):
        """Test the relate node command with JSON format."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_get_connection.return_value = MagicMock()
        expected_data = [
            {
                "type": "pr",
                "id": "pr:42",
                "title": "Add login feature",
                "timestamp": "2023-01-01T12:00:00",
                "number": 42,
                "state": "merged",
                "url": "https://github.com/org/repo/pull/42"
            }
        ]
        mock_get_related_nodes.return_value = expected_data

        # Run command
        result = runner.invoke(app, ["relate", "node", "commit:abc123", "--format", "json"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        actual_data = json.loads(result.stdout)
        self.assertEqual(actual_data, expected_data)

    @patch("arc_memory.cli.relate.get_related_nodes")
    @patch("arc_memory.sql.db.get_connection")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_relate_node_no_results(self, mock_exists, mock_ensure_arc_dir, mock_get_connection, mock_get_related_nodes):
        """Test the relate node command with no results."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_get_connection.return_value = MagicMock()
        mock_get_related_nodes.return_value = []

        # Run command
        result = runner.invoke(app, ["relate", "node", "commit:abc123"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No related nodes found for commit:abc123", result.stdout)

    @patch("arc_memory.sql.db.get_connection")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_relate_node_no_database(self, mock_exists, mock_ensure_arc_dir, mock_get_connection):
        """Test the relate node command with no database."""
        # Setup mocks
        mock_exists.return_value = True  # File exists but database connection fails
        mock_ensure_arc_dir.return_value = MagicMock()
        from arc_memory.errors import DatabaseError
        mock_get_connection.side_effect = DatabaseError("Failed to connect to database: unable to open database file")

        # Run command
        result = runner.invoke(app, ["relate", "node", "commit:abc123"])

        # Check result
        self.assertEqual(result.exit_code, 1)  # Error is not handled gracefully in relate command
        self.assertIn("Error", result.stdout)
        self.assertIn("Failed to connect to database", result.stdout)

    @patch("arc_memory.cli.relate.get_related_nodes")
    @patch("arc_memory.sql.db.get_connection")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_relate_node_with_relationship_filter(self, mock_exists, mock_ensure_arc_dir, mock_get_connection, mock_get_related_nodes):
        """Test the relate node command with relationship type filter."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_get_connection.return_value = MagicMock()
        mock_get_related_nodes.return_value = [
            {
                "type": "pr",
                "id": "pr:42",
                "title": "Add login feature",
                "timestamp": "2023-01-01T12:00:00",
                "number": 42,
                "state": "merged",
                "url": "https://github.com/org/repo/pull/42"
            }
        ]

        # Run command with relationship filter
        result = runner.invoke(app, ["relate", "node", "commit:abc123", "--rel", "MERGES"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Add login feature", result.stdout)

        # Verify that the relationship type was passed to get_related_nodes
        mock_get_related_nodes.assert_called_once_with(
            mock_get_connection.return_value,
            "commit:abc123",
            10,  # default max_results
            "MERGES"  # relationship_type
        )
