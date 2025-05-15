"""Tests for architecture query methods in the SDK."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from arc_memory.sdk import Arc
from arc_memory.sdk.errors import SDKError, AdapterError, QueryError
from arc_memory.schema.models import NodeType


class TestArchitectureQueries(unittest.TestCase):
    """Tests for architecture query methods in the SDK."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test databases
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        # Create the database file to avoid existence check errors
        with open(self.db_path, 'w') as f:
            f.write('')

        # Create a mock adapter
        self.mock_adapter = MagicMock()
        self.mock_adapter.get_name.return_value = "mock"
        self.mock_adapter.is_connected.return_value = True

        # Patch the get_adapter function to return our mock adapter
        self.get_adapter_patcher = patch("arc_memory.sdk.core.get_db_adapter", return_value=self.mock_adapter)
        self.mock_get_adapter = self.get_adapter_patcher.start()

        # Patch the get_db_path function to return our test path
        self.get_db_path_patcher = patch("arc_memory.sdk.core.get_db_path", return_value=self.db_path)
        self.mock_get_db_path = self.get_db_path_patcher.start()

        # Create a test repository path
        self.repo_path = Path(self.temp_dir.name) / "test-repo"
        self.repo_path.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        self.get_adapter_patcher.stop()
        self.get_db_path_patcher.stop()
        self.temp_dir.cleanup()

    def test_get_architecture_components_all(self):
        """Test getting all architecture components."""
        # Set up the mock adapter to return a repository
        self.mock_adapter.conn = MagicMock()
        mock_repo_row = {
            "id": "repository:test-repo",
            "name": "test-repo",
            "url": "https://github.com/test-org/test-repo",
            "local_path": str(self.repo_path.absolute()),
            "default_branch": "main",
            "metadata": '{}'
        }

        # Set up the mock adapter to return architecture components
        mock_components = [
            {
                "id": "system:test-system",
                "type": "system",
                "title": "Test System",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            },
            {
                "id": "service:test-service",
                "type": "service",
                "title": "Test Service",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            },
            {
                "id": "component:test-service/test-component",
                "type": "component",
                "title": "Test Component",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            },
            {
                "id": "interface:test-service/test-interface",
                "type": "interface",
                "title": "Test Interface",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            }
        ]

        # Set up the mock adapter to return the repository and components
        self.mock_adapter.conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=mock_repo_row)),
            MagicMock(fetchall=MagicMock(return_value=mock_components))
        ]

        # Create an Arc instance and call get_architecture_components
        arc = Arc(repo_path=self.repo_path)
        components = arc.get_architecture_components()

        # Verify that the adapter's execute method was called with the correct query
        self.mock_adapter.conn.execute.assert_called_with(
            unittest.mock.ANY,  # We don't care about the exact SQL query
            ("repository:test-repo",)
        )

        # Verify that the result is correct
        self.assertEqual(len(components), 4)
        component_types = [c["type"] for c in components]
        self.assertIn("system", component_types)
        self.assertIn("service", component_types)
        self.assertIn("component", component_types)
        self.assertIn("interface", component_types)

    def test_get_architecture_components_filtered_by_type(self):
        """Test getting architecture components filtered by type."""
        # Set up the mock adapter to return a repository
        self.mock_adapter.conn = MagicMock()
        mock_repo_row = {
            "id": "repository:test-repo",
            "name": "test-repo",
            "url": "https://github.com/test-org/test-repo",
            "local_path": str(self.repo_path.absolute()),
            "default_branch": "main",
            "metadata": '{}'
        }

        # Set up the mock adapter to return service components
        mock_services = [
            {
                "id": "service:test-service1",
                "type": "service",
                "title": "Test Service 1",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            },
            {
                "id": "service:test-service2",
                "type": "service",
                "title": "Test Service 2",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            }
        ]

        # Set up the mock adapter to return the repository and services
        self.mock_adapter.conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=mock_repo_row)),
            MagicMock(fetchall=MagicMock(return_value=mock_services))
        ]

        # Create an Arc instance and call get_architecture_components with a type filter
        arc = Arc(repo_path=self.repo_path)
        components = arc.get_architecture_components(component_type="service")

        # Verify that the adapter's execute method was called with the correct query
        self.mock_adapter.conn.execute.assert_called_with(
            unittest.mock.ANY,  # We don't care about the exact SQL query
            ("repository:test-repo", "service")
        )

        # Verify that the result is correct
        self.assertEqual(len(components), 2)
        for component in components:
            self.assertEqual(component["type"], "service")

    def test_get_architecture_components_filtered_by_parent(self):
        """Test getting architecture components filtered by parent."""
        # Set up the mock adapter to return a repository
        self.mock_adapter.conn = MagicMock()
        mock_repo_row = {
            "id": "repository:test-repo",
            "name": "test-repo",
            "url": "https://github.com/test-org/test-repo",
            "local_path": str(self.repo_path.absolute()),
            "default_branch": "main",
            "metadata": '{}'
        }

        # Set up the mock adapter to return all components
        mock_components = [
            {
                "id": "system:test-system",
                "type": "system",
                "title": "Test System",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            },
            {
                "id": "service:test-service1",
                "type": "service",
                "title": "Test Service 1",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            },
            {
                "id": "service:test-service2",
                "type": "service",
                "title": "Test Service 2",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            },
            {
                "id": "component:test-service1/test-component1",
                "type": "component",
                "title": "Test Component 1",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            },
            {
                "id": "component:test-service1/test-component2",
                "type": "component",
                "title": "Test Component 2",
                "repo_id": "repository:test-repo",
                "extra": '{}'
            }
        ]

        # Set up the mock adapter to return CONTAINS edges
        mock_edges = [
            {"src": "system:test-system", "dst": "service:test-service1", "rel": "CONTAINS"},
            {"src": "system:test-system", "dst": "service:test-service2", "rel": "CONTAINS"},
            {"src": "service:test-service1", "dst": "component:test-service1/test-component1", "rel": "CONTAINS"},
            {"src": "service:test-service1", "dst": "component:test-service1/test-component2", "rel": "CONTAINS"}
        ]

        # Set up the mock adapter to return the repository, components, and edges
        self.mock_adapter.conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=mock_repo_row)),
            MagicMock(fetchall=MagicMock(return_value=mock_components)),
            MagicMock(fetchall=MagicMock(return_value=[
                {"src": "service:test-service1", "dst": "component:test-service1/test-component1", "rel": "CONTAINS"},
                {"src": "service:test-service1", "dst": "component:test-service1/test-component2", "rel": "CONTAINS"}
            ]))
        ]

        # Create an Arc instance and call get_architecture_components with a parent filter
        arc = Arc(repo_path=self.repo_path)
        components = arc.get_architecture_components(parent_id="service:test-service1")

        # Verify that the adapter's execute methods were called with the correct queries
        self.mock_adapter.conn.execute.assert_any_call(
            unittest.mock.ANY,  # We don't care about the exact SQL query
            ("repository:test-repo",)
        )
        self.mock_adapter.conn.execute.assert_any_call(
            unittest.mock.ANY,  # We don't care about the exact SQL query
            ("service:test-service1",)
        )

        # Verify that the result is correct
        self.assertEqual(len(components), 2)
        component_ids = [c["id"] for c in components]
        self.assertIn("component:test-service1/test-component1", component_ids)
        self.assertIn("component:test-service1/test-component2", component_ids)


if __name__ == "__main__":
    unittest.main()
