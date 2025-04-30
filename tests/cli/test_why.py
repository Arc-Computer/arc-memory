"""Tests for the why command."""

import json
import unittest
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from arc_memory.cli import app

runner = CliRunner()


class TestWhyCommand(unittest.TestCase):
    """Tests for the why command."""

    @patch("arc_memory.cli.why.trace_history_for_file_line")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_file_text_format(self, mock_exists, mock_ensure_arc_dir, mock_trace):
        """Test the why file command with text format."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_trace.return_value = [
            {
                "type": "commit",
                "id": "commit:abc123",
                "title": "Fix bug in login form",
                "timestamp": "2023-01-01T12:00:00",
                "author": "John Doe",
                "sha": "abc123"
            }
        ]

        # Run command
        result = runner.invoke(app, ["why", "file", "src/main.py", "42"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Fix bug in login form", result.stdout)
        self.assertIn("John Doe", result.stdout)
        self.assertIn("abc123", result.stdout)

    @patch("arc_memory.cli.why.trace_history_for_file_line")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_file_json_format(self, mock_exists, mock_ensure_arc_dir, mock_trace):
        """Test the why file command with JSON format."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        expected_data = [
            {
                "type": "commit",
                "id": "commit:abc123",
                "title": "Fix bug in login form",
                "timestamp": "2023-01-01T12:00:00",
                "author": "John Doe",
                "sha": "abc123"
            }
        ]
        mock_trace.return_value = expected_data

        # Run command
        result = runner.invoke(app, ["why", "file", "src/main.py", "42", "--format", "json"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        actual_data = json.loads(result.stdout)
        self.assertEqual(actual_data, expected_data)

    @patch("arc_memory.cli.why.trace_history_for_file_line")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_file_markdown_format(self, mock_exists, mock_ensure_arc_dir, mock_trace):
        """Test the why file command with Markdown format."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_trace.return_value = [
            {
                "type": "commit",
                "id": "commit:abc123",
                "title": "Fix bug in login form",
                "timestamp": "2023-01-01T12:00:00",
                "author": "John Doe",
                "sha": "abc123"
            }
        ]

        # Run command
        result = runner.invoke(app, ["why", "file", "src/main.py", "42", "--format", "markdown"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Decision Trail for src/main.py:42", result.stdout)
        self.assertIn("Commit: Fix bug in login form", result.stdout)
        self.assertIn("John Doe", result.stdout)
        self.assertIn("abc123", result.stdout)

    @patch("arc_memory.cli.why.trace_history_for_file_line")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_file_no_results(self, mock_exists, mock_ensure_arc_dir, mock_trace):
        """Test the why file command with no results."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_trace.return_value = []

        # Run command
        result = runner.invoke(app, ["why", "file", "src/main.py", "42"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No history found for src/main.py:42", result.stdout)

    @patch("arc_memory.trace.trace_history_for_file_line")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_file_no_database(self, mock_exists, mock_ensure_arc_dir, mock_trace):
        """Test the why file command with no database."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        # Return empty results to simulate no history found
        mock_trace.return_value = []

        # Run command
        result = runner.invoke(app, ["why", "file", "src/main.py", "42"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No history found for src/main.py:42", result.stdout)
