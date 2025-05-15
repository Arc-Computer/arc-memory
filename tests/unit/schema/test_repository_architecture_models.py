"""Tests for repository identity and architecture schema models."""

import unittest
from datetime import datetime

from arc_memory.schema.models import (
    Node,
    NodeType,
    Edge,
    EdgeRel,
    RepositoryNode,
    SystemNode,
    ServiceNode,
    ComponentNode,
    InterfaceNode,
)


class TestRepositoryIdentityModels(unittest.TestCase):
    """Tests for repository identity models."""

    def test_repository_node_type(self):
        """Test that the REPOSITORY node type exists."""
        self.assertIn(NodeType.REPOSITORY, NodeType)
        self.assertEqual(NodeType.REPOSITORY.value, "repository")

    def test_repository_node_creation(self):
        """Test creating a repository node."""
        repo_node = RepositoryNode(
            id="repository:test-repo",
            title="Test Repository",
            name="test-repo",
            url="https://github.com/test-org/test-repo",
            local_path="/path/to/test-repo",
            default_branch="main",
            metadata={"description": "A test repository"}
        )

        # Check that the node was created correctly
        self.assertEqual(repo_node.id, "repository:test-repo")
        self.assertEqual(repo_node.type, NodeType.REPOSITORY)
        self.assertEqual(repo_node.title, "Test Repository")
        self.assertEqual(repo_node.name, "test-repo")
        self.assertEqual(repo_node.url, "https://github.com/test-org/test-repo")
        self.assertEqual(repo_node.local_path, "/path/to/test-repo")
        self.assertEqual(repo_node.default_branch, "main")
        self.assertEqual(repo_node.metadata, {"description": "A test repository"})

    def test_node_repo_id(self):
        """Test that nodes can have a repo_id."""
        node = Node(
            id="test:1",
            type=NodeType.COMMIT,
            title="Test Node",
            repo_id="repository:test-repo"
        )

        # Check that the repo_id was set correctly
        self.assertEqual(node.repo_id, "repository:test-repo")


class TestArchitectureSchemaModels(unittest.TestCase):
    """Tests for architecture schema models."""

    def test_architecture_node_types(self):
        """Test that the architecture node types exist."""
        self.assertIn(NodeType.SYSTEM, NodeType)
        self.assertEqual(NodeType.SYSTEM.value, "system")
        
        self.assertIn(NodeType.SERVICE, NodeType)
        self.assertEqual(NodeType.SERVICE.value, "service")
        
        self.assertIn(NodeType.COMPONENT, NodeType)
        self.assertEqual(NodeType.COMPONENT.value, "component")
        
        self.assertIn(NodeType.INTERFACE, NodeType)
        self.assertEqual(NodeType.INTERFACE.value, "interface")

    def test_architecture_edge_relationships(self):
        """Test that the architecture edge relationships exist."""
        self.assertIn(EdgeRel.CONTAINS, EdgeRel)
        self.assertEqual(EdgeRel.CONTAINS.value, "CONTAINS")
        
        self.assertIn(EdgeRel.EXPOSES, EdgeRel)
        self.assertEqual(EdgeRel.EXPOSES.value, "EXPOSES")
        
        self.assertIn(EdgeRel.CONSUMES, EdgeRel)
        self.assertEqual(EdgeRel.CONSUMES.value, "CONSUMES")
        
        self.assertIn(EdgeRel.COMMUNICATES_WITH, EdgeRel)
        self.assertEqual(EdgeRel.COMMUNICATES_WITH.value, "COMMUNICATES_WITH")

    def test_system_node_creation(self):
        """Test creating a system node."""
        system_node = SystemNode(
            id="system:test-system",
            title="Test System",
            name="test-system",
            description="A test system",
            repo_id="repository:test-repo"
        )

        # Check that the node was created correctly
        self.assertEqual(system_node.id, "system:test-system")
        self.assertEqual(system_node.type, NodeType.SYSTEM)
        self.assertEqual(system_node.title, "Test System")
        self.assertEqual(system_node.name, "test-system")
        self.assertEqual(system_node.description, "A test system")
        self.assertEqual(system_node.repo_id, "repository:test-repo")

    def test_service_node_creation(self):
        """Test creating a service node."""
        service_node = ServiceNode(
            id="service:test-service",
            title="Test Service",
            name="test-service",
            description="A test service",
            system_id="system:test-system",
            repo_id="repository:test-repo"
        )

        # Check that the node was created correctly
        self.assertEqual(service_node.id, "service:test-service")
        self.assertEqual(service_node.type, NodeType.SERVICE)
        self.assertEqual(service_node.title, "Test Service")
        self.assertEqual(service_node.name, "test-service")
        self.assertEqual(service_node.description, "A test service")
        self.assertEqual(service_node.system_id, "system:test-system")
        self.assertEqual(service_node.repo_id, "repository:test-repo")

    def test_component_node_creation(self):
        """Test creating a component node."""
        component_node = ComponentNode(
            id="component:test-service/test-component",
            title="Test Component",
            name="test-component",
            description="A test component",
            service_id="service:test-service",
            files=["path/to/file1.py", "path/to/file2.py"],
            repo_id="repository:test-repo"
        )

        # Check that the node was created correctly
        self.assertEqual(component_node.id, "component:test-service/test-component")
        self.assertEqual(component_node.type, NodeType.COMPONENT)
        self.assertEqual(component_node.title, "Test Component")
        self.assertEqual(component_node.name, "test-component")
        self.assertEqual(component_node.description, "A test component")
        self.assertEqual(component_node.service_id, "service:test-service")
        self.assertEqual(component_node.files, ["path/to/file1.py", "path/to/file2.py"])
        self.assertEqual(component_node.repo_id, "repository:test-repo")

    def test_interface_node_creation(self):
        """Test creating an interface node."""
        interface_node = InterfaceNode(
            id="interface:test-service/test-interface",
            title="Test Interface",
            name="test-interface",
            description="A test interface",
            service_id="service:test-service",
            interface_type="api",
            repo_id="repository:test-repo"
        )

        # Check that the node was created correctly
        self.assertEqual(interface_node.id, "interface:test-service/test-interface")
        self.assertEqual(interface_node.type, NodeType.INTERFACE)
        self.assertEqual(interface_node.title, "Test Interface")
        self.assertEqual(interface_node.name, "test-interface")
        self.assertEqual(interface_node.description, "A test interface")
        self.assertEqual(interface_node.service_id, "service:test-service")
        self.assertEqual(interface_node.interface_type, "api")
        self.assertEqual(interface_node.repo_id, "repository:test-repo")


if __name__ == "__main__":
    unittest.main()
