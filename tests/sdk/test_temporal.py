"""Tests for the temporal module."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from arc_memory.sdk.models import HistoryEntry
from arc_memory.sdk.temporal import (
    get_entity_history,
    _get_entity_references,
    _determine_change_type,
    _filter_by_date_range,
    _include_related_entities
)


class TestTemporal(unittest.TestCase):
    """Tests for the temporal module."""

    def test_get_entity_history(self):
        """Test the get_entity_history function."""
        # Create a mock adapter
        mock_adapter = MagicMock()

        # Set up the mock adapter to return a node
        mock_adapter.get_node_by_id.return_value = {
            "id": "file:123",
            "type": "file",
            "title": "login.py",
            "body": "Login functionality",
            "timestamp": "2023-01-01T12:00:00"
        }

        # Mock the reference functions
        with patch("arc_memory.sdk.temporal._get_entity_references") as mock_get_refs:
            with patch("arc_memory.sdk.temporal._filter_by_date_range") as mock_filter:
                with patch("arc_memory.sdk.temporal._include_related_entities") as mock_include:
                    # Set up the mocks to return some results
                    mock_get_refs.return_value = [
                        {
                            "id": "commit:456",
                            "type": "commit",
                            "title": "Fix login bug",
                            "body": "This fixes a bug in the login flow",
                            "timestamp": "2023-01-02T12:00:00",
                            "properties": {"author": "John Doe"},
                            "change_type": "modified",
                            "previous_version": None
                        },
                        {
                            "id": "pr:789",
                            "type": "pr",
                            "title": "Login bug fix",
                            "body": "This PR fixes the login bug",
                            "timestamp": "2023-01-03T12:00:00",
                            "properties": {"number": 789},
                            "change_type": "referenced",
                            "previous_version": None
                        }
                    ]
                    mock_filter.return_value = mock_get_refs.return_value
                    mock_include.return_value = mock_filter.return_value

                    # Call the function
                    result = get_entity_history(
                        adapter=mock_adapter,
                        entity_id="file:123",
                        start_date=datetime(2023, 1, 1),
                        end_date=datetime(2023, 1, 31),
                        include_related=True
                    )

                    # Check the result
                    self.assertEqual(len(result), 2)
                    self.assertIsInstance(result[0], HistoryEntry)
                    self.assertEqual(result[0].id, "commit:456")
                    self.assertEqual(result[0].type, "commit")
                    self.assertEqual(result[0].title, "Fix login bug")
                    self.assertEqual(result[0].body, "This fixes a bug in the login flow")
                    self.assertEqual(result[0].timestamp.isoformat(), "2023-01-02T12:00:00")
                    self.assertEqual(result[0].properties, {"author": "John Doe"})
                    self.assertEqual(result[0].change_type, "modified")
                    self.assertIsNone(result[0].previous_version)

                    self.assertIsInstance(result[1], HistoryEntry)
                    self.assertEqual(result[1].id, "pr:789")
                    self.assertEqual(result[1].type, "pr")
                    self.assertEqual(result[1].title, "Login bug fix")
                    self.assertEqual(result[1].body, "This PR fixes the login bug")
                    self.assertEqual(result[1].timestamp.isoformat(), "2023-01-03T12:00:00")
                    self.assertEqual(result[1].properties, {"number": 789})
                    self.assertEqual(result[1].change_type, "referenced")
                    self.assertIsNone(result[1].previous_version)

                    # Check that the adapter methods were called with the right arguments
                    mock_adapter.get_node_by_id.assert_called_once_with("file:123")
                    mock_get_refs.assert_called_once_with(mock_adapter, "file:123")
                    mock_filter.assert_called_once_with(
                        mock_get_refs.return_value,
                        datetime(2023, 1, 1),
                        datetime(2023, 1, 31)
                    )
                    mock_include.assert_called_once_with(
                        mock_adapter,
                        mock_filter.return_value
                    )

    def test_get_entity_references(self):
        """Test the _get_entity_references function."""
        # Create a mock adapter
        mock_adapter = MagicMock()

        # Set up the mock adapter to return some edges and nodes
        mock_adapter.get_edges_by_dst.return_value = [
            {"src": "commit:456", "dst": "file:123", "rel": "MODIFIES"},
            {"src": "pr:789", "dst": "file:123", "rel": "MENTIONS"}
        ]
        mock_adapter.get_node_by_id.side_effect = lambda id: {
            "commit:456": {
                "id": "commit:456",
                "type": "commit",
                "title": "Fix login bug",
                "body": "This fixes a bug in the login flow",
                "timestamp": "2023-01-02T12:00:00",
                "extra": {"author": "John Doe"}
            },
            "pr:789": {
                "id": "pr:789",
                "type": "pr",
                "title": "Login bug fix",
                "body": "This PR fixes the login bug",
                "timestamp": "2023-01-03T12:00:00",
                "extra": {"number": 789}
            }
        }.get(id)

        # Call the function
        result = _get_entity_references(mock_adapter, "file:123")

        # Check the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "pr:789")  # Sorted by timestamp, newest first
        self.assertEqual(result[0]["type"], "pr")
        self.assertEqual(result[0]["title"], "Login bug fix")
        self.assertEqual(result[0]["change_type"], "referenced")

        self.assertEqual(result[1]["id"], "commit:456")
        self.assertEqual(result[1]["type"], "commit")
        self.assertEqual(result[1]["title"], "Fix login bug")
        self.assertEqual(result[1]["change_type"], "modified")

    def test_determine_change_type(self):
        """Test the _determine_change_type function."""
        self.assertEqual(_determine_change_type("MODIFIES"), "modified")
        self.assertEqual(_determine_change_type("CREATES"), "created")
        self.assertEqual(_determine_change_type("MENTIONS"), "referenced")
        self.assertEqual(_determine_change_type("MERGES"), "merged")
        self.assertEqual(_determine_change_type("DEPENDS_ON"), "depends_on")
        self.assertEqual(_determine_change_type("IMPLEMENTS"), "implements")
        self.assertEqual(_determine_change_type("DECIDES"), "decides")
        self.assertEqual(_determine_change_type("UNKNOWN"), "referenced")  # Default

    def test_filter_by_date_range(self):
        """Test the _filter_by_date_range function."""
        # Create some test references
        references = [
            {
                "id": "commit:456",
                "timestamp": "2023-01-02T12:00:00"
            },
            {
                "id": "pr:789",
                "timestamp": "2023-01-03T12:00:00"
            },
            {
                "id": "issue:012",
                "timestamp": "2023-01-04T12:00:00"
            }
        ]

        # Test filtering with start date only
        result = _filter_by_date_range(
            references,
            start_date=datetime(2023, 1, 3),
            end_date=None
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "pr:789")
        self.assertEqual(result[1]["id"], "issue:012")

        # Test filtering with end date only
        result = _filter_by_date_range(
            references,
            start_date=None,
            end_date=datetime(2023, 1, 3, 13, 0, 0)  # After pr:789 but before issue:012
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "commit:456")
        self.assertEqual(result[1]["id"], "pr:789")

        # Test filtering with both start and end date
        result = _filter_by_date_range(
            references,
            start_date=datetime(2023, 1, 2, 13, 0, 0),  # After commit:456
            end_date=datetime(2023, 1, 3, 13, 0, 0)  # After pr:789 but before issue:012
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "pr:789")


if __name__ == "__main__":
    unittest.main()
