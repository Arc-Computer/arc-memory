"""Tests for database initialization and error handling."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

from arc_memory.errors import DatabaseError, DatabaseInitializationError, DatabaseNotFoundError
from arc_memory.sql.db import (
    DEFAULT_DB_PATH,
    add_nodes_and_edges,
    get_connection,
    get_edge_count,
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
        
        # Check that the file doesn't exist (since we're using a mock)
        self.assertFalse(DEFAULT_DB_PATH.exists())

    def test_get_connection_missing_db(self):
        """Test getting a connection to a missing database."""
        # Try to get a connection to a non-existent database
        with self.assertRaises(DatabaseNotFoundError):
            get_connection(self.db_path)

    def test_get_connection_no_check(self):
        """Test getting a connection without checking if the file exists."""
        # This should not raise an error, but the connection will fail when used
        with self.assertRaises(DatabaseError):
            conn = get_connection(self.db_path, check_exists=False)
            # This will fail because the database doesn't exist
            get_node_count(conn)

    def test_init_db_error_handling(self):
        """Test error handling during database initialization."""
        # Test with invalid path
        invalid_path = Path("/nonexistent/directory/db.db")
        with self.assertRaises(DatabaseInitializationError):
            init_db(invalid_path)

        # Test with dependency import error
        with patch("arc_memory.sql.db.apsw", None):
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = ImportError("No module named 'apsw'")
                with self.assertRaises(DatabaseInitializationError) as context:
                    init_db(self.db_path)
                self.assertIn("apsw", str(context.exception))

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


if __name__ == "__main__":
    unittest.main()
