"""Tests for the decision trail module."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from arc_memory.sdk.decision_trail import get_decision_trail
from arc_memory.sdk.models import DecisionTrailEntry


class TestDecisionTrail(unittest.TestCase):
    """Tests for the decision trail module."""

    @patch("arc_memory.sdk.decision_trail.trace_history_for_file_line")
    def test_get_decision_trail(self, mock_trace_history):
        """Test the get_decision_trail function."""
        # Set up the mock
        mock_trace_history.return_value = [
            {
                "id": "commit:123",
                "type": "commit",
                "title": "Fix bug in login",
                "body": "This fixes a bug in the login flow because users were getting logged out.",
                "timestamp": "2023-01-01T12:00:00",
                "author": "John Doe",
                "sha": "abc123"
            },
            {
                "id": "pr:456",
                "type": "pr",
                "title": "Login bug fix",
                "body": "This PR fixes the login bug that was causing users to be logged out.",
                "timestamp": "2023-01-02T12:00:00",
                "number": 456,
                "state": "merged",
                "url": "https://github.com/org/repo/pull/456"
            }
        ]

        # Create a mock adapter
        mock_adapter = MagicMock()
        mock_adapter.db_path = "/path/to/db"

        # Call the function
        result = get_decision_trail(
            adapter=mock_adapter,
            file_path="src/login.py",
            line_number=42,
            max_results=5,
            max_hops=3,
            include_rationale=True
        )

        # Check the result
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], DecisionTrailEntry)
        self.assertEqual(result[0].id, "commit:123")
        self.assertEqual(result[0].type, "commit")
        self.assertEqual(result[0].title, "Fix bug in login")
        self.assertEqual(result[0].body, "This fixes a bug in the login flow because users were getting logged out.")
        self.assertEqual(result[0].timestamp.isoformat(), "2023-01-01T12:00:00")
        self.assertEqual(result[0].properties["author"], "John Doe")
        self.assertEqual(result[0].properties["sha"], "abc123")
        self.assertEqual(result[0].trail_position, 0)
        self.assertIsNotNone(result[0].rationale)
        self.assertIn("because", result[0].rationale)

        self.assertIsInstance(result[1], DecisionTrailEntry)
        self.assertEqual(result[1].id, "pr:456")
        self.assertEqual(result[1].type, "pr")
        self.assertEqual(result[1].title, "Login bug fix")
        self.assertEqual(result[1].body, "This PR fixes the login bug that was causing users to be logged out.")
        self.assertEqual(result[1].timestamp.isoformat(), "2023-01-02T12:00:00")
        self.assertEqual(result[1].properties["number"], 456)
        self.assertEqual(result[1].properties["state"], "merged")
        self.assertEqual(result[1].properties["url"], "https://github.com/org/repo/pull/456")
        self.assertEqual(result[1].trail_position, 1)
        self.assertIsNotNone(result[1].rationale)

        # Check that trace_history_for_file_line was called with the right arguments
        mock_trace_history.assert_called_once()
        _, kwargs = mock_trace_history.call_args
        self.assertEqual(kwargs["file_path"], "src/login.py")
        self.assertEqual(kwargs["line_number"], 42)
        self.assertEqual(kwargs["max_results"], 5)
        self.assertEqual(kwargs["max_hops"], 3)
        self.assertTrue(isinstance(kwargs["db_path"], Path))


if __name__ == "__main__":
    unittest.main()
