"""Tests for the CLI trace command."""

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from arc_memory.cli.trace import app, Format


class TestCliTrace(unittest.TestCase):
    """Test the CLI trace command."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a CLI runner
        self.runner = CliRunner()

        # Create a temporary directory for the test repository
        self.repo_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.repo_dir.name)

        # Create a temporary SQLite database
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.conn = sqlite3.connect(self.db_path)

        # Create the necessary tables
        self.conn.execute("""
            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                type TEXT,
                title TEXT,
                body TEXT,
                extra TEXT
            )
        """)

        self.conn.execute("""
            CREATE TABLE edges (
                src TEXT,
                dst TEXT,
                rel TEXT,
                PRIMARY KEY (src, dst, rel)
            )
        """)

        # Insert test data
        self.insert_test_data()

    def tearDown(self):
        """Tear down test fixtures."""
        self.repo_dir.cleanup()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def insert_test_data(self):
        """Insert test data into the database."""
        # Insert nodes
        nodes = [
            ("commit:abc123", "commit", "Fix bug in authentication", "Detailed commit message", 
             '{"author": "John Doe", "sha": "abc123def456", "ts": "2023-04-15T14:32:10Z"}'),
            ("pr:42", "pr", "PR #42: Fix authentication bug", "PR description", 
             '{"number": 42, "state": "MERGED", "url": "https://github.com/example/repo/pull/42", "ts": "2023-04-16T09:15:22Z"}'),
            ("issue:123", "issue", "Issue #123: Authentication fails", "Issue description", 
             '{"number": 123, "state": "closed", "url": "https://github.com/example/repo/issues/123", "ts": "2023-04-10T11:20:05Z"}'),
            ("adr:001", "adr", "ADR-001: Authentication Strategy", "ADR content", 
             '{"status": "accepted", "decision_makers": ["lead_architect@example.com"], "path": "docs/adr/001-authentication.md", "ts": "2023-04-05T10:00:00Z"}'),
        ]

        self.conn.executemany(
            "INSERT INTO nodes (id, type, title, body, extra) VALUES (?, ?, ?, ?, ?)",
            nodes
        )

        # Insert edges
        edges = [
            ("commit:abc123", "pr:42", "MERGES"),
            ("pr:42", "issue:123", "MENTIONS"),
            ("adr:001", "issue:123", "DECIDES"),
        ]

        self.conn.executemany(
            "INSERT INTO edges (src, dst, rel) VALUES (?, ?, ?)",
            edges
        )

        self.conn.commit()

    @patch("arc_memory.cli.trace.trace_history_for_file_line")
    @patch("pathlib.Path.exists")
    def test_trace_file_text_format(self, mock_exists, mock_trace):
        """Test the trace file command with text format."""
        # Mock the database path
        mock_exists.return_value = True

        # Mock the trace_history_for_file_line function
        mock_trace.return_value = [
            {
                "type": "commit",
                "id": "commit:abc123",
                "title": "Fix bug in authentication",
                "timestamp": "2023-04-15T14:32:10Z",
                "author": "John Doe",
                "sha": "abc123def456"
            },
            {
                "type": "pr",
                "id": "pr:42",
                "title": "PR #42: Fix authentication bug",
                "timestamp": "2023-04-16T09:15:22Z",
                "number": 42,
                "state": "MERGED",
                "url": "https://github.com/example/repo/pull/42"
            }
        ]

        # Run the command with text format
        result = self.runner.invoke(app, ["file", "src/main.py", "42", "--format", "text"])

        # Check the result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("History for src/main.py:42", result.stdout)
        self.assertIn("commit", result.stdout)
        self.assertIn("pr", result.stdout)
        # The text might be truncated in the table output
        self.assertIn("Fix bug in", result.stdout)
        self.assertIn("authentication", result.stdout)
        self.assertIn("PR #42", result.stdout)

    @patch("arc_memory.cli.trace.trace_history_for_file_line")
    @patch("pathlib.Path.exists")
    def test_trace_file_json_format(self, mock_exists, mock_trace):
        """Test the trace file command with JSON format."""
        # Mock the database path
        mock_exists.return_value = True

        # Mock the trace_history_for_file_line function
        expected_results = [
            {
                "type": "commit",
                "id": "commit:abc123",
                "title": "Fix bug in authentication",
                "timestamp": "2023-04-15T14:32:10Z",
                "author": "John Doe",
                "sha": "abc123def456"
            },
            {
                "type": "pr",
                "id": "pr:42",
                "title": "PR #42: Fix authentication bug",
                "timestamp": "2023-04-16T09:15:22Z",
                "number": 42,
                "state": "MERGED",
                "url": "https://github.com/example/repo/pull/42"
            }
        ]
        mock_trace.return_value = expected_results

        # Run the command with JSON format
        result = self.runner.invoke(app, ["file", "src/main.py", "42", "--format", "json"])

        # Check the result
        self.assertEqual(result.exit_code, 0)
        
        # Parse the JSON output
        output_json = json.loads(result.stdout)
        
        # Verify the JSON structure
        self.assertEqual(len(output_json), 2)
        self.assertEqual(output_json[0]["type"], "commit")
        self.assertEqual(output_json[0]["id"], "commit:abc123")
        self.assertEqual(output_json[0]["title"], "Fix bug in authentication")
        self.assertEqual(output_json[0]["timestamp"], "2023-04-15T14:32:10Z")
        self.assertEqual(output_json[0]["author"], "John Doe")
        self.assertEqual(output_json[0]["sha"], "abc123def456")
        
        self.assertEqual(output_json[1]["type"], "pr")
        self.assertEqual(output_json[1]["id"], "pr:42")
        self.assertEqual(output_json[1]["title"], "PR #42: Fix authentication bug")
        self.assertEqual(output_json[1]["timestamp"], "2023-04-16T09:15:22Z")
        self.assertEqual(output_json[1]["number"], 42)
        self.assertEqual(output_json[1]["state"], "MERGED")
        self.assertEqual(output_json[1]["url"], "https://github.com/example/repo/pull/42")

    @patch("arc_memory.cli.trace.trace_history_for_file_line")
    @patch("pathlib.Path.exists")
    def test_trace_file_json_format_empty_results(self, mock_exists, mock_trace):
        """Test the trace file command with JSON format and empty results."""
        # Mock the database path
        mock_exists.return_value = True

        # Mock the trace_history_for_file_line function to return empty results
        mock_trace.return_value = []

        # Run the command with JSON format
        result = self.runner.invoke(app, ["file", "src/main.py", "42", "--format", "json"])

        # Check the result
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout.strip(), "[]")

    @patch("pathlib.Path.exists")
    def test_trace_file_database_not_found(self, mock_exists):
        """Test the trace file command when the database is not found."""
        # Mock the database path
        mock_exists.return_value = False

        # Run the command with text format
        result = self.runner.invoke(app, ["file", "src/main.py", "42", "--format", "text"])

        # Check the result
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Database not found", result.stdout)

        # Run the command with JSON format
        result = self.runner.invoke(app, ["file", "src/main.py", "42", "--format", "json"])

        # Check the result
        self.assertEqual(result.exit_code, 1)
        # Error messages are in stdout for Typer CLI runner
        self.assertIn("Error: Database not found", result.stdout)

    @patch("arc_memory.cli.trace.trace_history_for_file_line")
    @patch("pathlib.Path.exists")
    def test_trace_file_exception(self, mock_exists, mock_trace):
        """Test the trace file command when an exception occurs."""
        # Mock the database path
        mock_exists.return_value = True

        # Mock the trace_history_for_file_line function to raise an exception
        mock_trace.side_effect = Exception("Test exception")

        # Run the command with text format
        result = self.runner.invoke(app, ["file", "src/main.py", "42", "--format", "text"])

        # Check the result
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Test exception", result.stdout)

        # Run the command with JSON format
        result = self.runner.invoke(app, ["file", "src/main.py", "42", "--format", "json"])

        # Check the result
        self.assertEqual(result.exit_code, 1)
        # Error messages are in stdout for Typer CLI runner
        self.assertIn("Error: Test exception", result.stdout)


if __name__ == "__main__":
    unittest.main()
