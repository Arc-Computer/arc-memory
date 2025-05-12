"""Tests for the relationships module."""

import unittest
from unittest.mock import MagicMock, patch

from arc_memory.sdk.models import EntityDetails, RelatedEntity
from arc_memory.sdk.relationships import get_related_entities, get_entity_details


class TestRelationships(unittest.TestCase):
    """Tests for the relationships module."""

    def test_get_related_entities(self):
        """Test the get_related_entities function."""
        # Create a mock adapter
        mock_adapter = MagicMock()

        # Set up the mock adapter to return some edges and nodes
        mock_adapter.get_edges_by_src.return_value = [
            {"src": "commit:123", "dst": "file:456", "rel": "MODIFIES", "properties": {"lines_added": 10}}
        ]
        mock_adapter.get_edges_by_dst.return_value = [
            {"src": "pr:789", "dst": "commit:123", "rel": "MERGES", "properties": {}}
        ]
        mock_adapter.get_node_by_id.side_effect = lambda id: {
            "file:456": {"id": "file:456", "type": "file", "title": "login.py"},
            "pr:789": {"id": "pr:789", "type": "pr", "title": "Fix login bug"}
        }.get(id)

        # Call the function
        result = get_related_entities(
            adapter=mock_adapter,
            entity_id="commit:123",
            relationship_types=None,
            direction="both",
            max_results=10,
            include_properties=True
        )

        # Check the result
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], RelatedEntity)
        self.assertEqual(result[0].id, "file:456")
        self.assertEqual(result[0].type, "file")
        self.assertEqual(result[0].title, "login.py")
        self.assertEqual(result[0].relationship, "MODIFIES")
        self.assertEqual(result[0].direction, "outgoing")
        self.assertEqual(result[0].properties, {"lines_added": 10})

        self.assertIsInstance(result[1], RelatedEntity)
        self.assertEqual(result[1].id, "pr:789")
        self.assertEqual(result[1].type, "pr")
        self.assertEqual(result[1].title, "Fix login bug")
        self.assertEqual(result[1].relationship, "MERGES")
        self.assertEqual(result[1].direction, "incoming")
        self.assertEqual(result[1].properties, {})

        # Check that the adapter methods were called with the right arguments
        mock_adapter.get_edges_by_src.assert_called_once_with("commit:123")
        mock_adapter.get_edges_by_dst.assert_called_once_with("commit:123")
        mock_adapter.get_node_by_id.assert_any_call("file:456")
        mock_adapter.get_node_by_id.assert_any_call("pr:789")

    def test_get_related_entities_with_filter(self):
        """Test the get_related_entities function with relationship filter."""
        # Create a mock adapter
        mock_adapter = MagicMock()

        # Set up the mock adapter to return some edges and nodes
        mock_adapter.get_edges_by_src.return_value = [
            {"src": "commit:123", "dst": "file:456", "rel": "MODIFIES", "properties": {"lines_added": 10}},
            {"src": "commit:123", "dst": "file:789", "rel": "MENTIONS", "properties": {}}
        ]
        mock_adapter.get_edges_by_dst.return_value = [
            {"src": "pr:789", "dst": "commit:123", "rel": "MERGES", "properties": {}}
        ]
        mock_adapter.get_node_by_id.side_effect = lambda id: {
            "file:456": {"id": "file:456", "type": "file", "title": "login.py"},
            "file:789": {"id": "file:789", "type": "file", "title": "README.md"},
            "pr:789": {"id": "pr:789", "type": "pr", "title": "Fix login bug"}
        }.get(id)

        # Call the function with a relationship filter
        result = get_related_entities(
            adapter=mock_adapter,
            entity_id="commit:123",
            relationship_types=["MODIFIES"],
            direction="both",
            max_results=10,
            include_properties=True
        )

        # Check the result
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], RelatedEntity)
        self.assertEqual(result[0].id, "file:456")
        self.assertEqual(result[0].type, "file")
        self.assertEqual(result[0].title, "login.py")
        self.assertEqual(result[0].relationship, "MODIFIES")
        self.assertEqual(result[0].direction, "outgoing")
        self.assertEqual(result[0].properties, {"lines_added": 10})

    def test_get_entity_details(self):
        """Test the get_entity_details function."""
        # Create a mock adapter
        mock_adapter = MagicMock()

        # Set up the mock adapter to return a node
        mock_adapter.get_node_by_id.return_value = {
            "id": "commit:123",
            "type": "commit",
            "title": "Fix login bug",
            "body": "This fixes a bug in the login flow.",
            "timestamp": "2023-01-01T12:00:00",
            "extra": {
                "author": "John Doe",
                "sha": "abc123"
            }
        }

        # Mock the get_related_entities function
        with patch("arc_memory.sdk.relationships.get_related_entities") as mock_get_related:
            mock_get_related.return_value = [
                RelatedEntity(
                    id="file:456",
                    type="file",
                    title="login.py",
                    relationship="MODIFIES",
                    direction="outgoing",
                    properties={"lines_added": 10}
                )
            ]

            # Call the function
            result = get_entity_details(
                adapter=mock_adapter,
                entity_id="commit:123",
                include_related=True
            )

            # Check the result
            self.assertIsInstance(result, EntityDetails)
            self.assertEqual(result.id, "commit:123")
            self.assertEqual(result.type, "commit")
            self.assertEqual(result.title, "Fix login bug")
            self.assertEqual(result.body, "This fixes a bug in the login flow.")
            self.assertEqual(result.timestamp.isoformat(), "2023-01-01T12:00:00")
            self.assertEqual(result.properties, {
                "author": "John Doe",
                "sha": "abc123"
            })
            self.assertEqual(len(result.related_entities), 1)
            self.assertEqual(result.related_entities[0].id, "file:456")
            self.assertEqual(result.related_entities[0].type, "file")
            self.assertEqual(result.related_entities[0].title, "login.py")
            self.assertEqual(result.related_entities[0].relationship, "MODIFIES")
            self.assertEqual(result.related_entities[0].direction, "outgoing")
            self.assertEqual(result.related_entities[0].properties, {"lines_added": 10})

            # Check that the adapter methods were called with the right arguments
            mock_adapter.get_node_by_id.assert_called_once_with("commit:123")
            mock_get_related.assert_called_once_with(
                adapter=mock_adapter,
                entity_id="commit:123",
                max_results=20,
                callback=None
            )


if __name__ == "__main__":
    unittest.main()
