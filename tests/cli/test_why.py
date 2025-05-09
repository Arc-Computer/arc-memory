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

    # Tests for the new natural language query command

    @patch("arc_memory.semantic_search.process_query")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_query_text_format(self, mock_exists, mock_ensure_arc_dir, mock_process_query):
        """Test the why query command with text format."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_process_query.return_value = {
            "understanding": "You want to know who implemented the authentication feature",
            "summary": "John Doe implemented authentication in PR #42",
            "answer": "The authentication feature was implemented by John Doe in pull request #42, which was merged on January 1, 2023. The PR included changes to the login form and user authentication mechanisms.",
            "results": [
                {
                    "type": "pr",
                    "id": "pr:42",
                    "title": "Implement authentication feature",
                    "timestamp": "2023-01-01T12:00:00",
                    "number": 42,
                    "state": "merged",
                    "url": "https://github.com/example/repo/pull/42",
                    "relevance": 10
                }
            ],
            "confidence": 8
        }

        # Run command
        result = runner.invoke(app, ["why", "query", "Who implemented the authentication feature?"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("John Doe implemented authentication in PR #42", result.stdout)
        self.assertIn("Implement authentication feature", result.stdout)
        self.assertIn("You want to know who implemented the authentication feature", result.stdout)
        self.assertIn("Confidence", result.stdout)
        self.assertIn("8", result.stdout)

    @patch("arc_memory.semantic_search.process_query")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_query_json_format(self, mock_exists, mock_ensure_arc_dir, mock_process_query):
        """Test the why query command with JSON format."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        expected_data = {
            "understanding": "You want to know who implemented the authentication feature",
            "summary": "John Doe implemented authentication in PR #42",
            "answer": "The authentication feature was implemented by John Doe in pull request #42, which was merged on January 1, 2023.",
            "results": [
                {
                    "type": "pr",
                    "id": "pr:42",
                    "title": "Implement authentication feature",
                    "timestamp": "2023-01-01T12:00:00",
                    "number": 42,
                    "state": "merged",
                    "url": "https://github.com/example/repo/pull/42",
                    "relevance": 10
                }
            ],
            "confidence": 8
        }
        mock_process_query.return_value = expected_data

        # Run command
        result = runner.invoke(app, ["why", "query", "Who implemented the authentication feature?", "--format", "json"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        
        # Extract the JSON part from the output
        import re
        json_match = re.search(r'\{.*\}', result.stdout, re.DOTALL)
        self.assertIsNotNone(json_match, "No JSON found in output")
        
        # Compare the extracted JSON
        if json_match:
            actual_data = json.loads(json_match.group(0))
            self.assertEqual(actual_data, expected_data)

    @patch("arc_memory.semantic_search.process_query")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_query_markdown_format(self, mock_exists, mock_ensure_arc_dir, mock_process_query):
        """Test the why query command with Markdown format."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_process_query.return_value = {
            "understanding": "You want to know who implemented the authentication feature",
            "summary": "John Doe implemented authentication in PR #42",
            "answer": "The authentication feature was implemented by John Doe in pull request #42, which was merged on January 1, 2023.",
            "results": [
                {
                    "type": "pr",
                    "id": "pr:42",
                    "title": "Implement authentication feature",
                    "timestamp": "2023-01-01T12:00:00",
                    "number": 42,
                    "state": "merged",
                    "url": "https://github.com/example/repo/pull/42",
                    "relevance": 10
                }
            ],
            "confidence": 8
        }

        # Run command
        result = runner.invoke(app, ["why", "query", "Who implemented the authentication feature?", "--format", "markdown"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Answer: John Doe implemented authentication in PR #42", result.stdout)
        self.assertIn("Query Understanding", result.stdout)
        self.assertIn("Detailed Answer", result.stdout)
        self.assertIn("Pr: Implement authentication feature", result.stdout)
        self.assertIn("PR: #42", result.stdout)
        self.assertIn("Confidence", result.stdout)
        self.assertIn("8/10", result.stdout)

    @patch("arc_memory.semantic_search.process_query")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_query_no_results(self, mock_exists, mock_ensure_arc_dir, mock_process_query):
        """Test the why query command with no results."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_process_query.return_value = {
            "understanding": "You want to know about a feature that doesn't exist",
            "summary": "No relevant information found",
            "results": []
        }

        # Run command
        result = runner.invoke(app, ["why", "query", "Who implemented the non-existent feature?"])

        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No relevant information found", result.stdout)
        self.assertIn("You want to know about a feature that doesn't exist", result.stdout)

    @patch("arc_memory.semantic_search.process_query")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_query_with_depth_parameter(self, mock_exists, mock_ensure_arc_dir, mock_process_query):
        """Test the why query command with depth parameter."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_process_query.return_value = {
            "understanding": "You want to know about the database schema changes",
            "summary": "Database schema was changed to support user profiles",
            "answer": "The database schema was changed in PR #50 to support user profiles.",
            "results": [
                {
                    "type": "pr",
                    "id": "pr:50",
                    "title": "Change database schema for user profiles",
                    "timestamp": "2023-02-01T12:00:00",
                    "number": 50,
                    "state": "merged",
                    "url": "https://github.com/example/repo/pull/50",
                    "relevance": 10
                }
            ],
            "confidence": 7
        }

        # Run command
        result = runner.invoke(app, ["why", "query", "Why was the database schema changed?", "--depth", "deep"])

        # Verify mock was called with correct parameters
        mock_process_query.assert_called_once()
        args, kwargs = mock_process_query.call_args
        self.assertEqual(kwargs.get("max_hops"), 4)  # deep = 4 hops
        
        # Check result
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Database schema was changed to support user profiles", result.stdout)

    @patch("arc_memory.llm.ollama_client.ensure_ollama_available")
    @patch("arc_memory.sql.db.ensure_arc_dir")
    @patch("pathlib.Path.exists")
    def test_why_query_no_ollama(self, mock_exists, mock_ensure_arc_dir, mock_ensure_ollama):
        """Test the why query command when Ollama is not available."""
        # Setup mocks
        mock_exists.return_value = True
        mock_ensure_arc_dir.return_value = MagicMock()
        mock_ensure_ollama.return_value = False

        # We need to also patch the process_query function to simulate the error
        with patch("arc_memory.semantic_search.process_query") as mock_process_query:
            mock_process_query.return_value = {
                "error": "Ollama is not available. Please install it from https://ollama.ai"
            }
            
            # Run command
            result = runner.invoke(app, ["why", "query", "Who implemented the authentication feature?"])
            
            # Check result
            self.assertIn("Ollama is not available", result.stdout)
