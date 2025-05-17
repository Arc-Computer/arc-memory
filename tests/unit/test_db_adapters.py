"""Tests for database adapters."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from arc_memory.db import get_adapter
from arc_memory.db.base import DatabaseAdapter
from arc_memory.db.sqlite_adapter import SQLiteAdapter
from arc_memory.db.neo4j_adapter import Neo4jAdapter
from arc_memory.errors import DatabaseError, DatabaseInitializationError
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType


class TestDatabaseAdapters(unittest.TestCase):
    """Tests for database adapters."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test databases
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_get_adapter_sqlite(self):
        """Test getting a SQLite adapter."""
        adapter = get_adapter("sqlite")
        self.assertIsInstance(adapter, SQLiteAdapter)
        self.assertEqual(adapter.get_name(), "sqlite")

    def test_get_adapter_neo4j(self):
        """Test getting a Neo4j adapter."""
        adapter = get_adapter("neo4j")
        self.assertIsInstance(adapter, Neo4jAdapter)
        self.assertEqual(adapter.get_name(), "neo4j")

    def test_get_adapter_invalid(self):
        """Test getting an invalid adapter."""
        with self.assertRaises(ValueError):
            get_adapter("invalid")

    @patch("arc_memory.config.get_config")
    def test_get_adapter_from_config(self, mock_get_config):
        """Test getting an adapter from the configuration."""
        # Mock the configuration
        mock_get_config.return_value = {"database": {"adapter": "sqlite"}}

        # Get the adapter without specifying a type
        adapter = get_adapter()

        # Check that we got a SQLite adapter
        self.assertIsInstance(adapter, SQLiteAdapter)
        self.assertEqual(adapter.get_name(), "sqlite")


class TestSQLiteAdapter(unittest.TestCase):
    """Tests for SQLite adapter."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test databases
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        # Create a SQLite adapter
        self.adapter = SQLiteAdapter()

    def tearDown(self):
        """Clean up test environment."""
        if self.adapter.is_connected():
            self.adapter.disconnect()
        self.temp_dir.cleanup()

    def test_connect_disconnect(self):
        """Test connecting to and disconnecting from a database."""
        # Connect to the database
        self.adapter.connect({"db_path": self.db_path, "check_exists": False})

        # Check that we're connected
        self.assertTrue(self.adapter.is_connected())

        # Disconnect from the database
        self.adapter.disconnect()

        # Check that we're disconnected
        self.assertFalse(self.adapter.is_connected())

    def test_init_db(self):
        """Test initializing a database."""
        # Connect to the database
        self.adapter.connect({"db_path": self.db_path, "check_exists": False})

        # Initialize the database
        self.adapter.init_db()

        # Check that we can query the database
        self.assertEqual(self.adapter.get_node_count(), 0)
        self.assertEqual(self.adapter.get_edge_count(), 0)

    def test_add_nodes_and_edges(self):
        """Test adding nodes and edges to a database."""
        # Connect to the database
        self.adapter.connect({"db_path": self.db_path, "check_exists": False})

        # Initialize the database
        self.adapter.init_db()

        # Create test data
        nodes = [
            Node(
                id="test:1",
                type=NodeType.COMMIT,
                title="Test Node 1",
                body="Test Body 1",
                ts=datetime.now(),
                extra={"key1": "value1"}
            ),
            Node(
                id="test:2",
                type=NodeType.ISSUE,
                title="Test Node 2",
                body="Test Body 2",
                ts=datetime.now(),
                extra={"key2": "value2"}
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

        # Add the data
        self.adapter.add_nodes_and_edges(nodes, edges)

        # Check the counts
        self.assertEqual(self.adapter.get_node_count(), 2)
        self.assertEqual(self.adapter.get_edge_count(), 1)

        # Check that we can retrieve the nodes and edges
        node = self.adapter.get_node_by_id("test:1")
        self.assertIsNotNone(node)
        self.assertEqual(node["id"], "test:1")
        self.assertEqual(node["type"], NodeType.COMMIT.value.lower())  # Type is stored as lowercase
        self.assertEqual(node["title"], "Test Node 1")
        self.assertEqual(node["body"], "Test Body 1")
        self.assertEqual(node["extra"]["key1"], "value1")

        edges_by_src = self.adapter.get_edges_by_src("test:1")
        self.assertEqual(len(edges_by_src), 1)
        self.assertEqual(edges_by_src[0]["src"], "test:1")
        self.assertEqual(edges_by_src[0]["dst"], "test:2")
        self.assertEqual(edges_by_src[0]["rel"], "MENTIONS")
        self.assertEqual(edges_by_src[0]["properties"]["key"], "value")

        edges_by_dst = self.adapter.get_edges_by_dst("test:2")
        self.assertEqual(len(edges_by_dst), 1)
        self.assertEqual(edges_by_dst[0]["src"], "test:1")
        self.assertEqual(edges_by_dst[0]["dst"], "test:2")
        self.assertEqual(edges_by_dst[0]["rel"], "MENTIONS")
        self.assertEqual(edges_by_dst[0]["properties"]["key"], "value")

    def test_metadata(self):
        """Test saving and retrieving metadata."""
        # Connect to the database
        self.adapter.connect({"db_path": self.db_path, "check_exists": False})

        # Initialize the database
        self.adapter.init_db()

        # Save metadata
        self.adapter.save_metadata("test_key", "test_value")

        # Retrieve metadata
        value = self.adapter.get_metadata("test_key")
        self.assertEqual(value, "test_value")

        # Get all metadata
        metadata = self.adapter.get_all_metadata()
        self.assertIn("test_key", metadata)
        self.assertEqual(metadata["test_key"], "test_value")

        # Test default value for non-existent key
        value = self.adapter.get_metadata("non_existent_key", "default_value")
        self.assertEqual(value, "default_value")

    def test_refresh_timestamps(self):
        """Test saving and retrieving refresh timestamps."""
        # Connect to the database
        self.adapter.connect({"db_path": self.db_path, "check_exists": False})

        # Initialize the database
        self.adapter.init_db()

        # Save refresh timestamp
        now = datetime.now()
        self.adapter.save_refresh_timestamp("github", now)

        # Retrieve refresh timestamp
        timestamp = self.adapter.get_refresh_timestamp("github")
        self.assertEqual(timestamp.isoformat(), now.isoformat())

        # Test non-existent source
        timestamp = self.adapter.get_refresh_timestamp("non_existent_source")
        self.assertIsNone(timestamp)

        # Save another refresh timestamp
        later = datetime.now()
        self.adapter.save_refresh_timestamp("linear", later)

        # Get all refresh timestamps
        timestamps = self.adapter.get_all_refresh_timestamps()
        self.assertEqual(len(timestamps), 2)
        self.assertIn("github", timestamps)
        self.assertIn("linear", timestamps)
        self.assertEqual(timestamps["github"].isoformat(), now.isoformat())
        self.assertEqual(timestamps["linear"].isoformat(), later.isoformat())

    def test_transactions(self):
        """Test transaction support."""
        # Connect to the database
        self.adapter.connect({"db_path": self.db_path, "check_exists": False})

        # Initialize the database
        self.adapter.init_db()

        # Begin a transaction
        transaction = self.adapter.begin_transaction()

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

        # Add the data
        self.adapter.add_nodes_and_edges(nodes, [])

        # Commit the transaction
        self.adapter.commit_transaction(transaction)

        # Check that the data was committed
        self.assertEqual(self.adapter.get_node_count(), 1)

        # Begin another transaction
        transaction = self.adapter.begin_transaction()

        # Create more test data
        nodes = [
            Node(
                id="test:2",
                type=NodeType.ISSUE,
                title="Test Node 2",
                body="Test Body 2",
                ts=datetime.now(),
                extra={"key2": "value2"}
            )
        ]

        # Add the data
        self.adapter.add_nodes_and_edges(nodes, [])

        # Rollback the transaction
        self.adapter.rollback_transaction(transaction)

        # Check that the data was not committed
        self.assertEqual(self.adapter.get_node_count(), 1)
