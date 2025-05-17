"""Tests for the query module."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from arc_memory.sdk.models import QueryResult
from arc_memory.sdk.query import query_knowledge_graph


class TestQuery(unittest.TestCase):
    """Tests for the query module."""

    @patch("arc_memory.sdk.query.process_query")
    def test_query_knowledge_graph(self, mock_process_query):
        """Test the query_knowledge_graph function."""
        # Set up the mock
        mock_process_query.return_value = {
            "answer": "This is the answer",
            "confidence": 8.5,
            "results": [{"id": "1", "type": "commit", "title": "Test commit"}],
            "understanding": "This is the understanding",
            "reasoning": "This is the reasoning",
            "execution_time": 1.5
        }

        # Create a mock adapter
        mock_adapter = MagicMock()
        mock_adapter.db_path = "/path/to/db"

        # Call the function
        result = query_knowledge_graph(
            adapter=mock_adapter,
            question="What is the meaning of life?",
            max_results=5,
            max_hops=3,
            include_causal=True
        )

        # Check the result
        self.assertIsInstance(result, QueryResult)
        self.assertEqual(result.query, "What is the meaning of life?")
        self.assertEqual(result.answer, "This is the answer")
        self.assertEqual(result.confidence, 8.5)  # Retained on 0-10 scale
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.evidence[0]["id"], "1")
        self.assertEqual(result.query_understanding, "This is the understanding")
        self.assertEqual(result.reasoning, "This is the reasoning")
        self.assertEqual(result.execution_time, 1.5)

        # Check that process_query was called with the right arguments
        mock_process_query.assert_called_once()
        _, kwargs = mock_process_query.call_args
        self.assertEqual(kwargs["query"], "What is the meaning of life?")
        self.assertEqual(kwargs["max_results"], 5)
        self.assertEqual(kwargs["max_hops"], 3)
        self.assertTrue(isinstance(kwargs["db_path"], Path))

    @patch("arc_memory.sdk.query.process_query")
    def test_query_knowledge_graph_error(self, mock_process_query):
        """Test the query_knowledge_graph function with an error."""
        # Set up the mock to return an error
        mock_process_query.return_value = {
            "error": "Something went wrong"
        }

        # Create a mock adapter
        mock_adapter = MagicMock()
        mock_adapter.db_path = "/path/to/db"

        # Call the function and check that it raises an exception
        with self.assertRaises(Exception) as context:
            query_knowledge_graph(
                adapter=mock_adapter,
                question="What is the meaning of life?",
                max_results=5,
                max_hops=3,
                include_causal=True
            )

        self.assertEqual(str(context.exception), "Failed to query knowledge graph: Something went wrong")


if __name__ == "__main__":
    unittest.main()
