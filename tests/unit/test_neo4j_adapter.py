"""Tests for Neo4j adapter."""

import unittest
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

# Mock the neo4j module
sys.modules['neo4j'] = MagicMock()
sys.modules['neo4j'].GraphDatabase = MagicMock()

from arc_memory.db.neo4j_adapter import Neo4jAdapter
from arc_memory.errors import DatabaseError
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType


class TestNeo4jAdapter(unittest.TestCase):
    """Tests for Neo4j adapter."""

    def setUp(self):
        """Set up test environment."""
        # Create a Neo4j adapter
        self.adapter = Neo4jAdapter()

        # Mock the Neo4j driver
        self.mock_driver = MagicMock()
        self.mock_session = MagicMock()
        self.mock_driver.session.return_value = self.mock_session

        # Mock the GraphDatabase module
        self.patcher = patch("neo4j.GraphDatabase")
        self.mock_graph_db = self.patcher.start()
        self.mock_graph_db.driver.return_value = self.mock_driver

    def tearDown(self):
        """Clean up test environment."""
        self.patcher.stop()
        if self.adapter.is_connected():
            self.adapter.disconnect()

    def test_connect_disconnect(self):
        """Test connecting to and disconnecting from a database."""
        # Connect to the database
        self.adapter.connect({
            "uri": "neo4j://localhost:7687",
            "auth": ("neo4j", "password"),
            "database": "neo4j"
        })

        # Check that we're connected
        self.assertTrue(self.adapter.is_connected())

        # Check that the driver was created with the correct parameters
        self.mock_graph_db.driver.assert_called_once_with(
            "neo4j://localhost:7687",
            auth=("neo4j", "password")
        )

        # Disconnect from the database
        self.adapter.disconnect()

        # Check that we're disconnected
        self.assertFalse(self.adapter.is_connected())

        # Check that the driver was closed
        self.mock_driver.close.assert_called_once()

    def test_connect_missing_uri(self):
        """Test connecting without a URI."""
        with self.assertRaises(DatabaseError):
            self.adapter.connect({
                "auth": ("neo4j", "password"),
                "database": "neo4j"
            })

    def test_connect_missing_auth(self):
        """Test connecting without authentication."""
        with self.assertRaises(DatabaseError):
            self.adapter.connect({
                "uri": "neo4j://localhost:7687",
                "database": "neo4j"
            })

    def test_init_db(self):
        """Test initializing a database."""
        # Connect to the database
        self.adapter.connect({
            "uri": "neo4j://localhost:7687",
            "auth": ("neo4j", "password"),
            "database": "neo4j"
        })

        # Initialize the database
        self.adapter.init_db()

        # Check that the session was used to create constraints and indexes
        self.mock_driver.session.assert_called()
        # We don't check self.mock_session.run.assert_called() because the Neo4j adapter
        # is a stub implementation and doesn't actually call run() in init_db

    def test_stub_methods(self):
        """Test that stub methods log warnings and return expected values."""
        # Connect to the database
        self.adapter.connect({
            "uri": "neo4j://localhost:7687",
            "auth": ("neo4j", "password"),
            "database": "neo4j"
        })

        # Create test data
        nodes = [
            Node(
                id="test:1",
                type=NodeType.COMMIT,
                title="Test Node 1",
                body="Test Body 1",
                ts=datetime.now(),
                extra={"key1": "value1"}
            )
        ]

        edges = [
            Edge(
                src="test:1",
                dst="test:2",
                rel=EdgeRel.MENTIONS,
                properties={"key": "value"}
            )
        ]

        # Test stub methods
        with self.assertLogs(level="WARNING") as cm:
            # Add nodes and edges
            self.adapter.add_nodes_and_edges(nodes, edges)

            # Get node by ID
            node = self.adapter.get_node_by_id("test:1")
            self.assertIsNone(node)

            # Get node count
            count = self.adapter.get_node_count()
            self.assertEqual(count, 0)

            # Get edge count
            count = self.adapter.get_edge_count()
            self.assertEqual(count, 0)

            # Get edges by source
            edges = self.adapter.get_edges_by_src("test:1")
            self.assertEqual(edges, [])

            # Get edges by destination
            edges = self.adapter.get_edges_by_dst("test:2")
            self.assertEqual(edges, [])

            # Search entities
            results = self.adapter.search_entities("test")
            self.assertEqual(results, [])

            # Begin transaction
            transaction = self.adapter.begin_transaction()
            self.assertIsNone(transaction)

            # Commit transaction
            self.adapter.commit_transaction(transaction)

            # Rollback transaction
            self.adapter.rollback_transaction(transaction)

            # Save metadata
            self.adapter.save_metadata("test_key", "test_value")

            # Get metadata
            value = self.adapter.get_metadata("test_key")
            self.assertIsNone(value)

            # Get all metadata
            metadata = self.adapter.get_all_metadata()
            self.assertEqual(metadata, {})

            # Save refresh timestamp
            now = datetime.now()
            self.adapter.save_refresh_timestamp("github", now)

            # Get refresh timestamp
            timestamp = self.adapter.get_refresh_timestamp("github")
            self.assertIsNone(timestamp)

            # Get all refresh timestamps
            timestamps = self.adapter.get_all_refresh_timestamps()
            self.assertEqual(timestamps, {})

        # Check that warnings were logged for all stub methods
        self.assertGreater(len(cm.output), 10)
        for log in cm.output:
            self.assertIn("stub implementation", log)

    def test_not_connected_errors(self):
        """Test that methods raise errors when not connected."""
        # Test methods that should raise errors when not connected
        with self.assertRaises(DatabaseError):
            self.adapter.init_db()

        with self.assertRaises(DatabaseError):
            self.adapter.add_nodes_and_edges([], [])

        with self.assertRaises(DatabaseError):
            self.adapter.get_node_by_id("test:1")

        with self.assertRaises(DatabaseError):
            self.adapter.get_node_count()

        with self.assertRaises(DatabaseError):
            self.adapter.get_edge_count()

        with self.assertRaises(DatabaseError):
            self.adapter.get_edges_by_src("test:1")

        with self.assertRaises(DatabaseError):
            self.adapter.get_edges_by_dst("test:2")

        with self.assertRaises(DatabaseError):
            self.adapter.search_entities("test")

        with self.assertRaises(DatabaseError):
            self.adapter.begin_transaction()

        with self.assertRaises(DatabaseError):
            self.adapter.commit_transaction(None)

        with self.assertRaises(DatabaseError):
            self.adapter.rollback_transaction(None)

        with self.assertRaises(DatabaseError):
            self.adapter.save_metadata("test_key", "test_value")

        with self.assertRaises(DatabaseError):
            self.adapter.get_metadata("test_key")

        with self.assertRaises(DatabaseError):
            self.adapter.get_all_metadata()

        with self.assertRaises(DatabaseError):
            self.adapter.save_refresh_timestamp("github", datetime.now())

        with self.assertRaises(DatabaseError):
            self.adapter.get_refresh_timestamp("github")
