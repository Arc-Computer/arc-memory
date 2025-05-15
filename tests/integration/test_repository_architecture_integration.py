"""Integration tests for repository identity and architecture schema features."""

import unittest
import json

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


class TestRepositoryArchitectureModels(unittest.TestCase):
    """Integration tests for repository identity and architecture schema models."""

    def test_repository_architecture_integration(self):
        """Test repository identity and architecture schema integration."""
        # Create a repository node
        repo_node = RepositoryNode(
            id="repository:test-repo",
            title="Test Repository",
            name="test-repo",
            url="https://github.com/test-org/test-repo",
            local_path="/path/to/test-repo",
            default_branch="main",
            metadata={"description": "A test repository"}
        )

        # Create a system node
        system_node = SystemNode(
            id="system:test-system",
            title="Test System",
            name="test-system",
            description="A test system",
            repo_id=repo_node.id
        )

        # Create service nodes
        service1_node = ServiceNode(
            id="service:service1",
            title="Service 1",
            name="service1",
            description="Service 1 description",
            system_id=system_node.id,
            repo_id=repo_node.id
        )

        service2_node = ServiceNode(
            id="service:service2",
            title="Service 2",
            name="service2",
            description="Service 2 description",
            system_id=system_node.id,
            repo_id=repo_node.id
        )

        # Create component nodes
        component1_node = ComponentNode(
            id="component:service1/component1",
            title="Component 1",
            name="component1",
            description="Component 1 description",
            service_id=service1_node.id,
            files=["service1/component1/file1.py", "service1/component1/file2.py"],
            repo_id=repo_node.id
        )

        component2_node = ComponentNode(
            id="component:service1/component2",
            title="Component 2",
            name="component2",
            description="Component 2 description",
            service_id=service1_node.id,
            files=["service1/component2/file3.py"],
            repo_id=repo_node.id
        )

        component3_node = ComponentNode(
            id="component:service2/component3",
            title="Component 3",
            name="component3",
            description="Component 3 description",
            service_id=service2_node.id,
            files=["service2/component3/file4.py", "service2/component3/file5.py"],
            repo_id=repo_node.id
        )

        # Create interface nodes
        interface1_node = InterfaceNode(
            id="interface:service1/api",
            title="API Interface",
            name="api",
            description="API Interface description",
            service_id=service1_node.id,
            interface_type="api",
            repo_id=repo_node.id
        )

        interface2_node = InterfaceNode(
            id="interface:service2/events",
            title="Events Interface",
            name="events",
            description="Events Interface description",
            service_id=service2_node.id,
            interface_type="event",
            repo_id=repo_node.id
        )

        # Create edges
        edges = [
            # System contains services
            Edge(src=system_node.id, dst=service1_node.id, rel=EdgeRel.CONTAINS),
            Edge(src=system_node.id, dst=service2_node.id, rel=EdgeRel.CONTAINS),

            # Services contain components
            Edge(src=service1_node.id, dst=component1_node.id, rel=EdgeRel.CONTAINS),
            Edge(src=service1_node.id, dst=component2_node.id, rel=EdgeRel.CONTAINS),
            Edge(src=service2_node.id, dst=component3_node.id, rel=EdgeRel.CONTAINS),

            # Components expose interfaces
            Edge(src=component1_node.id, dst=interface1_node.id, rel=EdgeRel.EXPOSES),
            Edge(src=component3_node.id, dst=interface2_node.id, rel=EdgeRel.EXPOSES),

            # Components communicate with each other
            Edge(src=component1_node.id, dst=component3_node.id, rel=EdgeRel.COMMUNICATES_WITH),
            Edge(src=component2_node.id, dst=component3_node.id, rel=EdgeRel.COMMUNICATES_WITH),

            # Components consume interfaces
            Edge(src=component2_node.id, dst=interface1_node.id, rel=EdgeRel.CONSUMES),
            Edge(src=component1_node.id, dst=interface2_node.id, rel=EdgeRel.CONSUMES)
        ]

        # Collect all nodes
        nodes = [
            repo_node,
            system_node,
            service1_node,
            service2_node,
            component1_node,
            component2_node,
            component3_node,
            interface1_node,
            interface2_node
        ]

        # Verify node types
        self.assertEqual(repo_node.type, NodeType.REPOSITORY)
        self.assertEqual(system_node.type, NodeType.SYSTEM)
        self.assertEqual(service1_node.type, NodeType.SERVICE)
        self.assertEqual(component1_node.type, NodeType.COMPONENT)
        self.assertEqual(interface1_node.type, NodeType.INTERFACE)

        # Verify edge relationships
        self.assertEqual(edges[0].rel, EdgeRel.CONTAINS)
        self.assertEqual(edges[5].rel, EdgeRel.EXPOSES)
        self.assertEqual(edges[7].rel, EdgeRel.COMMUNICATES_WITH)
        self.assertEqual(edges[9].rel, EdgeRel.CONSUMES)

        # Verify repository references
        for node in nodes[1:]:  # Skip repo_node
            self.assertEqual(node.repo_id, repo_node.id)

        # Verify parent-child relationships
        self.assertEqual(service1_node.system_id, system_node.id)
        self.assertEqual(service2_node.system_id, system_node.id)
        self.assertEqual(component1_node.service_id, service1_node.id)
        self.assertEqual(component2_node.service_id, service1_node.id)
        self.assertEqual(component3_node.service_id, service2_node.id)
        self.assertEqual(interface1_node.service_id, service1_node.id)
        self.assertEqual(interface2_node.service_id, service2_node.id)

        # Verify interface types
        self.assertEqual(interface1_node.interface_type, "api")
        self.assertEqual(interface2_node.interface_type, "event")

        # Verify component files
        self.assertEqual(len(component1_node.files), 2)
        self.assertEqual(len(component2_node.files), 1)
        self.assertEqual(len(component3_node.files), 2)

        # Verify serialization/deserialization
        # Convert to dict and back to ensure the models can be serialized
        repo_dict = repo_node.model_dump()
        repo_node2 = RepositoryNode(**repo_dict)
        self.assertEqual(repo_node.id, repo_node2.id)
        self.assertEqual(repo_node.name, repo_node2.name)

        # Test JSON serialization
        repo_json = json.dumps(repo_dict)
        repo_dict2 = json.loads(repo_json)
        repo_node3 = RepositoryNode(**repo_dict2)
        self.assertEqual(repo_node.id, repo_node3.id)
        self.assertEqual(repo_node.name, repo_node3.name)


if __name__ == "__main__":
    unittest.main()
