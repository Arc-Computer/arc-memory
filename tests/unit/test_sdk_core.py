"""Tests for the Arc Memory SDK core."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from arc_memory.sdk import Arc
from arc_memory.sdk.errors import SDKError, AdapterError, QueryError, BuildError
from arc_memory.schema.models import Edge, EdgeRel, Node, NodeType


class TestArcCore(unittest.TestCase):
    """Tests for the Arc class."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test databases
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        
        # Create a mock adapter
        self.mock_adapter = MagicMock()
        self.mock_adapter.get_name.return_value = "mock"
        self.mock_adapter.is_connected.return_value = True
        
        # Patch the get_adapter function to return our mock adapter
        self.get_adapter_patcher = patch("arc_memory.sdk.core.get_adapter", return_value=self.mock_adapter)
        self.mock_get_adapter = self.get_adapter_patcher.start()
        
        # Patch the get_db_path function to return our test path
        self.get_db_path_patcher = patch("arc_memory.sdk.core.get_db_path", return_value=self.db_path)
        self.mock_get_db_path = self.get_db_path_patcher.start()

    def tearDown(self):
        """Clean up test environment."""
        self.get_adapter_patcher.stop()
        self.get_db_path_patcher.stop()
        self.temp_dir.cleanup()

    def test_initialization(self):
        """Test that Arc can be initialized."""
        arc = Arc(repo_path="./")
        self.assertIsNotNone(arc)
        self.assertEqual(arc.repo_path, Path("./"))
        self.assertIsNotNone(arc.adapter)
        
        # Verify that the adapter was connected
        self.mock_adapter.connect.assert_called_once()
        self.mock_adapter.init_db.assert_called_once()

    def test_initialization_with_adapter_type(self):
        """Test that Arc can be initialized with a specific adapter type."""
        arc = Arc(repo_path="./", adapter_type="sqlite")
        self.assertIsNotNone(arc)
        
        # Verify that get_adapter was called with the correct adapter type
        self.mock_get_adapter.assert_called_with("sqlite")

    def test_initialization_with_connection_params(self):
        """Test that Arc can be initialized with connection parameters."""
        connection_params = {"db_path": str(self.db_path)}
        arc = Arc(repo_path="./", connection_params=connection_params)
        self.assertIsNotNone(arc)
        
        # Verify that the adapter was connected with the correct parameters
        self.mock_adapter.connect.assert_called_with(connection_params)

    def test_get_node_by_id(self):
        """Test getting a node by ID."""
        # Set up the mock adapter to return a node
        node = {"id": "test", "type": "commit", "title": "Test Node"}
        self.mock_adapter.get_node_by_id.return_value = node
        
        # Create an Arc instance and call get_node_by_id
        arc = Arc(repo_path="./")
        result = arc.get_node_by_id("test")
        
        # Verify that the adapter's get_node_by_id method was called
        self.mock_adapter.get_node_by_id.assert_called_with("test")
        
        # Verify that the result is correct
        self.assertEqual(result, node)

    def test_add_nodes_and_edges(self):
        """Test adding nodes and edges."""
        # Create test nodes and edges
        nodes = [
            Node(id="node1", type=NodeType.COMMIT, title="Node 1"),
            Node(id="node2", type=NodeType.FILE, title="Node 2"),
        ]
        edges = [
            Edge(src="node1", dst="node2", rel=EdgeRel.MODIFIES),
        ]
        
        # Create an Arc instance and call add_nodes_and_edges
        arc = Arc(repo_path="./")
        arc.add_nodes_and_edges(nodes, edges)
        
        # Verify that the adapter's add_nodes_and_edges method was called
        self.mock_adapter.add_nodes_and_edges.assert_called_with(nodes, edges)

    def test_get_node_count(self):
        """Test getting the node count."""
        # Set up the mock adapter to return a count
        self.mock_adapter.get_node_count.return_value = 42
        
        # Create an Arc instance and call get_node_count
        arc = Arc(repo_path="./")
        count = arc.get_node_count()
        
        # Verify that the adapter's get_node_count method was called
        self.mock_adapter.get_node_count.assert_called_once()
        
        # Verify that the result is correct
        self.assertEqual(count, 42)

    def test_get_edge_count(self):
        """Test getting the edge count."""
        # Set up the mock adapter to return a count
        self.mock_adapter.get_edge_count.return_value = 24
        
        # Create an Arc instance and call get_edge_count
        arc = Arc(repo_path="./")
        count = arc.get_edge_count()
        
        # Verify that the adapter's get_edge_count method was called
        self.mock_adapter.get_edge_count.assert_called_once()
        
        # Verify that the result is correct
        self.assertEqual(count, 24)

    def test_context_manager(self):
        """Test using Arc as a context manager."""
        # Create an Arc instance using a context manager
        with Arc(repo_path="./") as arc:
            self.assertIsNotNone(arc)
        
        # Verify that the adapter's disconnect method was called
        self.mock_adapter.disconnect.assert_called_once()

    def test_error_handling(self):
        """Test error handling."""
        # Set up the mock adapter to raise an exception
        self.mock_adapter.get_node_by_id.side_effect = Exception("Test error")
        
        # Create an Arc instance and call get_node_by_id
        arc = Arc(repo_path="./")
        
        # Verify that the exception is converted to a QueryError
        with self.assertRaises(QueryError):
            arc.get_node_by_id("test")

if __name__ == "__main__":
    unittest.main()
