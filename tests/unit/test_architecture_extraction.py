"""Tests for architecture extraction module."""

import os
import tempfile
import unittest
from pathlib import Path

from arc_memory.process.architecture_extraction import extract_architecture
from arc_memory.schema.models import Node, NodeType, Edge, EdgeRel


class TestArchitectureExtraction(unittest.TestCase):
    """Tests for architecture extraction module."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test repository
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        
        # Create a mock repository structure
        # - repo_root/
        #   - service1/
        #     - component1/
        #       - api.py
        #       - file1.py
        #     - component2/
        #       - file2.py
        #   - service2/
        #     - component3/
        #       - events.py
        #       - file3.py
        
        # Create service1
        service1_path = self.repo_path / "service1"
        service1_path.mkdir()
        
        # Create component1
        component1_path = service1_path / "component1"
        component1_path.mkdir()
        (component1_path / "api.py").touch()
        (component1_path / "file1.py").touch()
        
        # Create component2
        component2_path = service1_path / "component2"
        component2_path.mkdir()
        (component2_path / "file2.py").touch()
        
        # Create service2
        service2_path = self.repo_path / "service2"
        service2_path.mkdir()
        
        # Create component3
        component3_path = service2_path / "component3"
        component3_path.mkdir()
        (component3_path / "events.py").touch()
        (component3_path / "file3.py").touch()
        
        # Create some non-service directories that should be ignored
        (self.repo_path / ".git").mkdir()
        (self.repo_path / "node_modules").mkdir()
        (self.repo_path / "venv").mkdir()

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_extract_architecture(self):
        """Test extracting architecture components."""
        # Extract architecture components
        repo_id = "repository:test-repo"
        nodes, edges = extract_architecture([], [], self.repo_path, repo_id)
        
        # Verify that the correct number of nodes and edges were extracted
        # Expected:
        # - 1 system node
        # - 2 service nodes
        # - 3 component nodes
        # - 2 interface nodes (api.py and events.py)
        self.assertEqual(len(nodes), 8)
        
        # Expected:
        # - 2 CONTAINS edges from system to services
        # - 3 CONTAINS edges from services to components
        # - 2 EXPOSES edges from components to interfaces
        self.assertEqual(len(edges), 7)
        
        # Verify that the system node was created correctly
        system_nodes = [n for n in nodes if n.type == NodeType.SYSTEM]
        self.assertEqual(len(system_nodes), 1)
        system_node = system_nodes[0]
        self.assertEqual(system_node.title, self.repo_path.name)
        self.assertEqual(system_node.repo_id, repo_id)
        
        # Verify that the service nodes were created correctly
        service_nodes = [n for n in nodes if n.type == NodeType.SERVICE]
        self.assertEqual(len(service_nodes), 2)
        service_names = [n.title for n in service_nodes]
        self.assertIn("service1", service_names)
        self.assertIn("service2", service_names)
        
        # Verify that all service nodes have the correct repo_id
        for service_node in service_nodes:
            self.assertEqual(service_node.repo_id, repo_id)
        
        # Verify that the component nodes were created correctly
        component_nodes = [n for n in nodes if n.type == NodeType.COMPONENT]
        self.assertEqual(len(component_nodes), 3)
        component_names = [n.title for n in component_nodes]
        self.assertIn("component1", component_names)
        self.assertIn("component2", component_names)
        self.assertIn("component3", component_names)
        
        # Verify that all component nodes have the correct repo_id
        for component_node in component_nodes:
            self.assertEqual(component_node.repo_id, repo_id)
        
        # Verify that the interface nodes were created correctly
        interface_nodes = [n for n in nodes if n.type == NodeType.INTERFACE]
        self.assertEqual(len(interface_nodes), 2)
        
        # Verify that all interface nodes have the correct repo_id
        for interface_node in interface_nodes:
            self.assertEqual(interface_node.repo_id, repo_id)
        
        # Verify that the CONTAINS edges were created correctly
        contains_edges = [e for e in edges if e.rel == EdgeRel.CONTAINS]
        self.assertEqual(len(contains_edges), 5)
        
        # Verify that the EXPOSES edges were created correctly
        exposes_edges = [e for e in edges if e.rel == EdgeRel.EXPOSES]
        self.assertEqual(len(exposes_edges), 2)

    def test_extract_architecture_empty_repo(self):
        """Test extracting architecture components from an empty repository."""
        # Create an empty repository
        empty_dir = tempfile.TemporaryDirectory()
        empty_repo_path = Path(empty_dir.name)
        
        try:
            # Extract architecture components
            repo_id = "repository:empty-repo"
            nodes, edges = extract_architecture([], [], empty_repo_path, repo_id)
            
            # Verify that only a system node was created
            self.assertEqual(len(nodes), 1)
            self.assertEqual(nodes[0].type, NodeType.SYSTEM)
            self.assertEqual(nodes[0].title, empty_repo_path.name)
            self.assertEqual(nodes[0].repo_id, repo_id)
            
            # Verify that no edges were created
            self.assertEqual(len(edges), 0)
        finally:
            empty_dir.cleanup()

    def test_extract_architecture_with_existing_nodes(self):
        """Test extracting architecture components with existing nodes."""
        # Create some existing nodes and edges
        existing_nodes = [
            Node(id="existing:1", type=NodeType.COMMIT, title="Existing Node 1"),
            Node(id="existing:2", type=NodeType.FILE, title="Existing Node 2")
        ]
        existing_edges = [
            Edge(src="existing:1", dst="existing:2", rel=EdgeRel.MODIFIES)
        ]
        
        # Extract architecture components
        repo_id = "repository:test-repo"
        nodes, edges = extract_architecture(existing_nodes, existing_edges, self.repo_path, repo_id)
        
        # Verify that the correct number of nodes and edges were extracted
        # (same as test_extract_architecture)
        self.assertEqual(len(nodes), 8)
        self.assertEqual(len(edges), 7)
        
        # Verify that the existing nodes and edges were not modified
        self.assertEqual(len(existing_nodes), 2)
        self.assertEqual(len(existing_edges), 1)


if __name__ == "__main__":
    unittest.main()
