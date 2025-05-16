"""Test the enhanced schema functionality."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta

from arc_memory.db.sqlite_adapter import SQLiteAdapter
from arc_memory.schema.models import Node, NodeType, Edge, EdgeRel


class TestEnhancedSchema(unittest.TestCase):
    """Test the enhanced schema functionality."""

    def setUp(self):
        """Set up the test environment."""
        # Create a temporary database file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")

        # Initialize the database
        self.adapter = SQLiteAdapter()
        self.adapter.connect({"db_path": self.db_path, "check_exists": False})
        self.adapter.init_db()

    def tearDown(self):
        """Clean up the test environment."""
        self.adapter.disconnect()
        self.temp_dir.cleanup()

    def test_node_with_enhanced_fields(self):
        """Test creating and retrieving a node with enhanced fields."""
        # Create a node with enhanced fields
        now = datetime.now()
        node = Node(
            id="test-node-1",
            type=NodeType.COMPONENT,
            title="Test Component",
            body="This is a test component",
            ts=now,
            repo_id="test-repo",
            created_at=now - timedelta(days=10),
            updated_at=now,
            valid_from=now - timedelta(days=10),
            valid_until=now + timedelta(days=365),
            metadata={"key1": "value1", "key2": 123, "nested": {"a": 1, "b": 2}},
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
            url="https://example.com/test"
        )

        # Add the node to the database
        self.adapter.add_nodes_and_edges([node], [])

        # Retrieve the node from the database
        result = self.adapter.get_node_by_id("test-node-1")

        # Check that all fields were stored and retrieved correctly
        self.assertEqual(result["id"], "test-node-1")
        self.assertEqual(result["type"], NodeType.COMPONENT.value)
        self.assertEqual(result["title"], "Test Component")
        self.assertEqual(result["body"], "This is a test component")
        self.assertEqual(result["repo_id"], "test-repo")

        # Check enhanced fields
        self.assertIsNotNone(result.get("created_at"))
        self.assertIsNotNone(result.get("updated_at"))
        self.assertIsNotNone(result.get("valid_from"))
        self.assertIsNotNone(result.get("valid_until"))

        # Check metadata
        self.assertIn("metadata", result)
        self.assertEqual(result["metadata"]["key1"], "value1")
        self.assertEqual(result["metadata"]["key2"], 123)
        self.assertEqual(result["metadata"]["nested"]["a"], 1)
        self.assertEqual(result["metadata"]["nested"]["b"], 2)

        # Check embedding
        self.assertIn("embedding", result)
        self.assertEqual(len(result["embedding"]), 5)

        # Check URL
        self.assertEqual(result["url"], "https://example.com/test")

        # Check backward compatibility with extra field
        self.assertIn("extra", result)
        self.assertEqual(result["extra"]["key1"], "value1")

    def test_backward_compatibility(self):
        """Test backward compatibility with nodes that don't have enhanced fields."""
        # Create a node without enhanced fields but with extra data
        node = Node(
            id="test-node-2",
            type=NodeType.FILE,
            title="Test File",
            body="This is a test file",
            ts=datetime.now(),
            repo_id="test-repo"
        )
        # Set extra directly to test backward compatibility
        node.extra = {"legacy": True}

        # Add the node to the database
        self.adapter.add_nodes_and_edges([node], [])

        # Retrieve the node from the database
        result = self.adapter.get_node_by_id("test-node-2")

        # Check that basic fields were stored and retrieved correctly
        self.assertEqual(result["id"], "test-node-2")
        self.assertEqual(result["type"], NodeType.FILE.value)
        self.assertEqual(result["title"], "Test File")
        self.assertEqual(result["body"], "This is a test file")
        self.assertEqual(result["repo_id"], "test-repo")

        # Check that extra field was stored correctly
        self.assertIn("extra", result)
        self.assertIn("legacy", result["extra"])
        self.assertTrue(result["extra"]["legacy"])

    def test_migration(self):
        """Test that the migration script works correctly."""
        # Create a node with only basic fields
        node = Node(
            id="test-node-3",
            type=NodeType.COMMIT,
            title="Test Commit",
            body="This is a test commit",
            ts=datetime.now(),
            repo_id="test-repo"
        )
        # Set extra directly to test migration
        node.extra = {"commit_info": "test"}

        # Add the node to the database
        self.adapter.add_nodes_and_edges([node], [])

        # Retrieve the node from the database
        result = self.adapter.get_node_by_id("test-node-3")

        # Check that extra field was stored correctly
        self.assertIn("extra", result)
        self.assertIn("commit_info", result["extra"])
        self.assertEqual(result["extra"]["commit_info"], "test")

        # Check that created_at and updated_at were populated from ts
        self.assertIn("created_at", result)
        self.assertIsNotNone(result["created_at"])
        self.assertIn("updated_at", result)
        self.assertIsNotNone(result["updated_at"])


if __name__ == "__main__":
    unittest.main()
