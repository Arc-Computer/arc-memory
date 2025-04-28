"""Tests for database initialization and error handling."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arc_memory.errors import DatabaseError, DatabaseInitializationError, DatabaseNotFoundError
from arc_memory.sql.db import (
    DEFAULT_DB_PATH,
    add_nodes_and_edges,
    ensure_connection,
    get_connection,
    get_edge_count,
    get_edges_by_src,
    get_edges_by_dst,
    get_node_by_id,
    get_node_count,
    init_db,
)


class TestDatabaseInitialization(unittest.TestCase):
    """Tests for database initialization and error handling."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test databases
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_init_db_creates_file(self):
        """Test that init_db creates a database file."""
        # Initialize the database
        conn = init_db(self.db_path)

        # Check that the file exists
        self.assertTrue(self.db_path.exists())

        # Check that we can query the database
        count = get_node_count(conn)
        self.assertEqual(count, 0)

    def test_init_db_test_mode(self):
        """Test initializing the database in test mode."""
        # Initialize the database in test mode
        conn = init_db(test_mode=True)

        # Check that we can query the mock database
        count = get_node_count(conn)
        self.assertEqual(count, 0)

        # Note: We can't reliably check if the default DB path exists or not
        # because other tests might have created it. Instead, we'll check
        # that the connection is a mock connection.
        self.assertTrue(hasattr(conn, 'nodes'))

    def test_get_connection_missing_db(self):
        """Test getting a connection to a missing database."""
        # Try to get a connection to a non-existent database
        with self.assertRaises(DatabaseNotFoundError):
            get_connection(self.db_path)

    def test_get_connection_no_check(self):
        """Test getting a connection without checking if the file exists."""
        # First initialize the database to create the file
        init_db(self.db_path)

        # Then delete the file
        self.db_path.unlink()

        # Now try to get a connection without checking if the file exists
        with self.assertRaises(Exception):  # Could be SQLite error or our custom error
            conn = get_connection(self.db_path, check_exists=False)
            # This will fail because the database doesn't exist
            get_node_count(conn)

    def test_init_db_error_handling(self):
        """Test error handling during database initialization."""
        # Test with invalid path
        invalid_path = Path("/nonexistent/directory/db.db")
        with self.assertRaises(DatabaseInitializationError):
            init_db(invalid_path)

    def test_add_nodes_edges_error_handling(self):
        """Test error handling when adding nodes and edges."""
        # Initialize the database
        conn = init_db(self.db_path)

        # Test with invalid input
        with self.assertRaises(TypeError):
            add_nodes_and_edges(conn, None, None)

    def test_test_mode_operations(self):
        """Test operations in test mode."""
        # Initialize the database in test mode
        conn = init_db(test_mode=True)

        # Check initial counts
        self.assertEqual(get_node_count(conn), 0)
        self.assertEqual(get_edge_count(conn), 0)

        # Add some test data
        from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel
        from datetime import datetime

        nodes = [
            Node(
                id="test:1",
                type=NodeType.COMMIT,
                title="Test Node",
                body="Test Body",
                ts=datetime.now(),
                extra={}
            )
        ]

        edges = [
            Edge(
                src="test:1",
                dst="test:2",
                rel=EdgeRel.MENTIONS,
                properties={}
            )
        ]

        # Add the data
        add_nodes_and_edges(conn, nodes, edges)

        # Check the counts
        self.assertEqual(get_node_count(conn), 1)
        self.assertEqual(get_edge_count(conn), 1)


class TestConnectionHandling(unittest.TestCase):
    """Tests for database connection handling."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test databases
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        # Initialize the database
        self.conn = init_db(self.db_path)

    def tearDown(self):
        """Clean up test environment."""
        self.conn.close()
        self.temp_dir.cleanup()

    def test_ensure_connection_with_connection(self):
        """Test ensure_connection with an existing connection."""
        # Pass an existing connection
        result = ensure_connection(self.conn)

        # Should return the same connection
        self.assertEqual(result, self.conn)

        # Should be able to use the connection
        count = get_node_count(result)
        self.assertEqual(count, 0)

    def test_ensure_connection_with_path(self):
        """Test ensure_connection with a path."""
        # Pass a Path object
        result = ensure_connection(self.db_path)

        # Should return a new connection
        self.assertNotEqual(result, self.conn)

        # Should be able to use the connection
        count = get_node_count(result)
        self.assertEqual(count, 0)

        # Clean up
        result.close()

    def test_ensure_connection_with_string_path(self):
        """Test ensure_connection with a string path."""
        # Pass a string path
        result = ensure_connection(str(self.db_path))

        # Should return a new connection
        self.assertNotEqual(result, self.conn)

        # Should be able to use the connection
        count = get_node_count(result)
        self.assertEqual(count, 0)

        # Clean up
        result.close()

    def test_ensure_connection_with_invalid_input(self):
        """Test ensure_connection with invalid input."""
        # Pass an invalid input
        with self.assertRaises(DatabaseError):
            ensure_connection(123)  # Not a connection or path

    def test_get_node_by_id_with_connection(self):
        """Test get_node_by_id with a connection."""
        # Should work with a connection
        result = get_node_by_id(self.conn, "nonexistent")
        self.assertIsNone(result)

    def test_get_node_by_id_with_path(self):
        """Test get_node_by_id with a path."""
        # Should work with a path
        result = get_node_by_id(self.db_path, "nonexistent")
        self.assertIsNone(result)

    def test_get_edges_by_src_with_connection(self):
        """Test get_edges_by_src with a connection."""
        # Should work with a connection
        result = get_edges_by_src(self.conn, "nonexistent")
        self.assertEqual(result, [])

    def test_get_edges_by_src_with_path(self):
        """Test get_edges_by_src with a path."""
        # Should work with a path
        result = get_edges_by_src(self.db_path, "nonexistent")
        self.assertEqual(result, [])

    def test_get_edges_by_dst_with_connection(self):
        """Test get_edges_by_dst with a connection."""
        # Should work with a connection
        result = get_edges_by_dst(self.conn, "nonexistent")
        self.assertEqual(result, [])

    def test_get_edges_by_dst_with_path(self):
        """Test get_edges_by_dst with a path."""
        # Should work with a path
        result = get_edges_by_dst(self.db_path, "nonexistent")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
