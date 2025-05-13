"""Tests for the semantic search module."""

import json
import unittest
from unittest.mock import patch, MagicMock
import re

from arc_memory.semantic_search import (
    process_query,
    _process_query_intent,
    _extract_json_from_llm_response,
    _search_knowledge_graph,
    _expand_search,
    _score_nodes,
    _generate_response
)


class TestExtractJson(unittest.TestCase):
    """Test the _extract_json_from_llm_response function."""

    def test_extract_json_block(self):
        """Test extracting JSON from a code block format."""
        response = """
        Here's the JSON:

        ```json
        {
            "key": "value",
            "number": 42
        }
        ```

        Hope this helps!
        """
        result = _extract_json_from_llm_response(response)
        self.assertEqual(result, {"key": "value", "number": 42})

    def test_extract_json_simple_block(self):
        """Test extracting JSON from a simple code block."""
        response = """
        Here's the JSON:

        ```
        {
            "key": "value",
            "number": 42
        }
        ```

        Hope this helps!
        """
        result = _extract_json_from_llm_response(response)
        self.assertEqual(result, {"key": "value", "number": 42})

    def test_extract_json_raw(self):
        """Test extracting JSON from raw text without code blocks."""
        response = """
        Here's the JSON:

        {
            "key": "value",
            "number": 42
        }

        Hope this helps!
        """
        result = _extract_json_from_llm_response(response)
        self.assertEqual(result, {"key": "value", "number": 42})

    def test_extract_json_invalid(self):
        """Test extracting JSON from invalid text."""
        response = "This contains no valid JSON."
        result = _extract_json_from_llm_response(response)
        self.assertIsNone(result)

    def test_extract_json_regex_fallback(self):
        """Test extracting JSON using the regex fallback."""
        response = """
        Let me think about this...

        The appropriate structure would be something like { "key": "value" } but I need to add more details.

        Actually, here's what I think:

        {
            "key": "value",
            "number": 42,
            "nested": {"child": true}
        }

        That looks right to me.
        """
        # Mock the re.search function to return a match that can be parsed as JSON
        with patch('re.search') as mock_search:
            # Create a mock match object
            mock_match = MagicMock()
            mock_match.group.return_value = '{"key": "value", "number": 42, "nested": {"child": true}}'
            mock_search.return_value = mock_match

            # Call the function
            result = _extract_json_from_llm_response(response)

            # Verify the result
            self.assertEqual(result, {"key": "value", "number": 42, "nested": {"child": True}})


class TestProcessQueryIntent(unittest.TestCase):
    """Test the _process_query_intent function."""

    @patch("arc_memory.semantic_search.OllamaClient")
    def test_process_query_intent(self, mock_ollama):
        """Test processing a query intent."""
        # Setup mock
        mock_client = MagicMock()
        mock_ollama.return_value = mock_client
        mock_client.generate_with_thinking.return_value = """
        Let me analyze this query.

        ```json
        {
            "understanding": "The user wants to know who implemented the authentication feature",
            "entity_types": ["pr", "commit"],
            "attributes": {
                "title_keywords": ["authentication", "login"]
            }
        }
        ```
        """

        # Call the function
        result = _process_query_intent("Who implemented the authentication feature?")

        # Verify results
        self.assertEqual(result["understanding"], "The user wants to know who implemented the authentication feature")
        self.assertEqual(result["entity_types"], ["pr", "commit"])
        self.assertEqual(result["attributes"]["title_keywords"], ["authentication", "login"])

    @patch("arc_memory.semantic_search.OllamaClient")
    def test_process_query_intent_failure(self, mock_ollama):
        """Test processing a query intent with failure."""
        # Setup mock
        mock_client = MagicMock()
        mock_ollama.return_value = mock_client
        mock_client.generate_with_thinking.return_value = "Invalid response with no JSON"

        # Call the function
        result = _process_query_intent("Who implemented the authentication feature?")

        # Verify results
        self.assertIsNone(result)


@patch("arc_memory.semantic_search.get_connection")
@patch("arc_memory.semantic_search.ensure_ollama_available")
class TestProcessQuery(unittest.TestCase):
    """Test the process_query function."""

    @patch("arc_memory.semantic_search._process_query_intent")
    @patch("arc_memory.semantic_search._search_knowledge_graph")
    @patch("arc_memory.semantic_search._generate_response")
    def test_process_query_success(self, mock_generate, mock_search, mock_intent, mock_ensure_ollama, mock_get_conn):
        """Test successfully processing a query."""
        # Setup mocks
        mock_ensure_ollama.return_value = True
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        mock_intent.return_value = {
            "understanding": "The user wants to know who implemented the authentication feature",
            "entity_types": ["pr", "commit"],
            "attributes": {
                "title_keywords": ["authentication", "login"]
            }
        }

        mock_search.return_value = [
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
        ]

        expected_response = {
            "understanding": "The user wants to know who implemented the authentication feature",
            "summary": "John Doe implemented authentication in PR #42",
            "answer": "The authentication feature was implemented by John Doe in pull request #42.",
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
        mock_generate.return_value = expected_response

        # Call the function
        result = process_query("dummy/path", "Who implemented the authentication feature?")

        # Verify results
        self.assertEqual(result, expected_response)
        mock_intent.assert_called_once()
        mock_search.assert_called_once()
        mock_generate.assert_called_once()

    def test_process_query_no_ollama(self, mock_ensure_ollama, mock_get_conn):
        """Test processing a query when Ollama is not available."""
        # Setup mocks
        mock_ensure_ollama.return_value = False

        # Call the function
        result = process_query("dummy/path", "Who implemented the authentication feature?")

        # Verify results
        self.assertEqual(result["error"], "Ollama is not available. Please install it from https://ollama.com/download")

    @patch("arc_memory.semantic_search._process_query_intent")
    def test_process_query_intent_failure(self, mock_intent, mock_ensure_ollama, mock_get_conn):
        """Test processing a query when intent processing fails."""
        # Setup mocks
        mock_ensure_ollama.return_value = True
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_intent.return_value = None

        # Call the function
        result = process_query("dummy/path", "Who implemented the authentication feature?")

        # Verify results
        self.assertEqual(result["error"], "Failed to process query intent")
        self.assertEqual(result["understanding"], "I couldn't understand your question. Please try rephrasing it.")

    @patch("arc_memory.semantic_search._process_query_intent")
    @patch("arc_memory.semantic_search._search_knowledge_graph")
    def test_process_query_no_results(self, mock_search, mock_intent, mock_ensure_ollama, mock_get_conn):
        """Test processing a query with no results."""
        # Setup mocks
        mock_ensure_ollama.return_value = True
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        mock_intent.return_value = {
            "understanding": "The user wants to know who implemented a non-existent feature",
            "entity_types": ["pr", "commit"],
            "attributes": {
                "title_keywords": ["nonexistent"]
            }
        }

        mock_search.return_value = []

        # Call the function
        result = process_query("dummy/path", "Who implemented the non-existent feature?")

        # Verify results
        self.assertEqual(result["understanding"], "The user wants to know who implemented a non-existent feature")
        self.assertEqual(result["summary"], "No relevant information found")
        self.assertEqual(result["results"], [])


if __name__ == "__main__":
    unittest.main()