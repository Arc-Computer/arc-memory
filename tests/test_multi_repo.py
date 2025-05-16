"""Tests for multi-repository support in Arc Memory."""

import os
import tempfile
from pathlib import Path
import unittest
import hashlib
import shutil

from arc_memory.sdk.core import Arc
from arc_memory.schema.models import Node, NodeType


class TestMultiRepositorySupport(unittest.TestCase):
    """Test multi-repository support in Arc Memory."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for test repositories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo1_path = Path(self.temp_dir.name) / "repo1"
        self.repo2_path = Path(self.temp_dir.name) / "repo2"

        # Create test repositories
        self.repo1_path.mkdir(exist_ok=True)
        self.repo2_path.mkdir(exist_ok=True)

        # Create a temporary database file
        self.db_path = Path(self.temp_dir.name) / "test_graph.db"

        # Initialize Arc with the first repository
        self.arc = Arc(
            repo_path=self.repo1_path,
            connection_params={"db_path": str(self.db_path), "check_exists": False}
        )

        # Generate repository IDs
        self.repo1_id = f"repository:{hashlib.md5(str(self.repo1_path.absolute()).encode()).hexdigest()}"
        self.repo2_id = f"repository:{hashlib.md5(str(self.repo2_path.absolute()).encode()).hexdigest()}"

    def tearDown(self):
        """Clean up test environment."""
        # Disconnect from the database
        if hasattr(self, 'arc') and self.arc:
            self.arc.adapter.disconnect()

        # Clean up temporary directory
        self.temp_dir.cleanup()

    def test_add_repository(self):
        """Test adding repositories to the knowledge graph."""
        # Ensure the first repository exists
        repo1_id = self.arc.ensure_repository(name="Repo 1")

        # Add the second repository
        repo2_id = self.arc.add_repository(self.repo2_path, name="Repo 2")

        # Check that both repositories exist
        repos = self.arc.list_repositories()
        self.assertEqual(len(repos), 2)

        # Check repository IDs
        self.assertEqual(repo1_id, self.repo1_id)
        self.assertEqual(repo2_id, self.repo2_id)

        # Check repository names
        repo_names = {repo["name"] for repo in repos}
        self.assertIn("Repo 1", repo_names)
        self.assertIn("Repo 2", repo_names)

    def test_active_repositories(self):
        """Test setting and getting active repositories."""
        # Ensure both repositories exist
        repo1_id = self.arc.ensure_repository(name="Repo 1")
        repo2_id = self.arc.add_repository(self.repo2_path, name="Repo 2")

        # By default, both repositories are active since we add them to active_repos when creating them
        active_repos = self.arc.get_active_repositories()
        self.assertEqual(len(active_repos), 2)
        active_ids = {repo["id"] for repo in active_repos}
        self.assertIn(repo1_id, active_ids)
        self.assertIn(repo2_id, active_ids)

        # Set only the first repository as active
        self.arc.set_active_repositories([repo1_id])

        # Check that only the first repository is active
        active_repos = self.arc.get_active_repositories()
        self.assertEqual(len(active_repos), 1)
        self.assertEqual(active_repos[0]["id"], repo1_id)

        # Set only the second repository as active
        self.arc.set_active_repositories([repo2_id])

        # Check that only the second repository is active
        active_repos = self.arc.get_active_repositories()
        self.assertEqual(len(active_repos), 1)
        self.assertEqual(active_repos[0]["id"], repo2_id)

    def test_repository_filtering(self):
        """Test filtering nodes by repository."""
        # Ensure both repositories exist
        repo1_id = self.arc.ensure_repository(name="Repo 1")
        repo2_id = self.arc.add_repository(self.repo2_path, name="Repo 2")

        # Add test nodes for each repository
        node1 = Node(
            id="test:node1",
            type=NodeType.DOCUMENT,
            title="Test Node 1",
            body="This is a test node for repository 1",
            repo_id=repo1_id
        )

        node2 = Node(
            id="test:node2",
            type=NodeType.DOCUMENT,
            title="Test Node 2",
            body="This is a test node for repository 2",
            repo_id=repo2_id
        )

        # Add nodes to the graph
        self.arc.add_nodes_and_edges([node1, node2], [])

        # Query with no repository filter (should return both nodes)
        self.arc.set_active_repositories([repo1_id, repo2_id])
        result = self.arc.adapter.get_nodes_by_type(NodeType.DOCUMENT)
        self.assertEqual(len(result), 2)

        # Query with repository 1 filter (should return only node1)
        result = self.arc.adapter.get_nodes_by_type(NodeType.DOCUMENT, [repo1_id])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "test:node1")

        # Query with repository 2 filter (should return only node2)
        result = self.arc.adapter.get_nodes_by_type(NodeType.DOCUMENT, [repo2_id])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "test:node2")

    def test_build_repository(self):
        """Test building repositories."""
        # Ensure both repositories exist
        repo1_id = self.arc.ensure_repository(name="Repo 1")
        repo2_id = self.arc.add_repository(self.repo2_path, name="Repo 2")

        # Create test Git-like structure in repo1
        (self.repo1_path / ".git").mkdir(exist_ok=True)
        with open(self.repo1_path / "file1.txt", "w") as f:
            f.write("Test file 1")

        # Create test Git-like structure in repo2
        (self.repo2_path / ".git").mkdir(exist_ok=True)
        with open(self.repo2_path / "file2.txt", "w") as f:
            f.write("Test file 2")

        # Mock the build process (since we can't actually run Git commands in tests)
        # We'll just add some nodes that would normally be created during build

        # Add nodes for repo1
        node1 = Node(
            id="file:repo1/file1.txt",
            type=NodeType.FILE,
            title="file1.txt",
            body="Test file 1",
            repo_id=repo1_id
        )
        self.arc.add_nodes_and_edges([node1], [])

        # Add nodes for repo2
        node2 = Node(
            id="file:repo2/file2.txt",
            type=NodeType.FILE,
            title="file2.txt",
            body="Test file 2",
            repo_id=repo2_id
        )
        self.arc.add_nodes_and_edges([node2], [])

        # Query for files in repo1
        result = self.arc.adapter.get_nodes_by_type(NodeType.FILE, [repo1_id])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "file1.txt")

        # Query for files in repo2
        result = self.arc.adapter.get_nodes_by_type(NodeType.FILE, [repo2_id])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "file2.txt")

    def test_cross_repository_edges(self):
        """Test edges between nodes in different repositories."""
        from arc_memory.schema.models import Edge, EdgeRel

        # Ensure both repositories exist
        repo1_id = self.arc.ensure_repository(name="Repo 1")
        repo2_id = self.arc.add_repository(self.repo2_path, name="Repo 2")

        # Add test nodes for each repository
        node1 = Node(
            id="component:auth-service",
            type=NodeType.COMPONENT,
            title="Auth Service",
            body="Authentication service",
            repo_id=repo1_id
        )

        node2 = Node(
            id="component:user-service",
            type=NodeType.COMPONENT,
            title="User Service",
            body="User management service",
            repo_id=repo2_id
        )

        # Create a cross-repository edge
        edge = Edge(
            src="component:auth-service",
            dst="component:user-service",
            rel=EdgeRel.DEPENDS_ON,
            properties={"weight": 1.0}
        )

        # Add nodes and edge to the graph
        self.arc.add_nodes_and_edges([node1, node2], [edge])

        # Query for the edge
        query = """
        SELECT * FROM edges
        WHERE src = ? AND dst = ? AND rel = ?
        """
        result = self.arc.adapter.execute_query(
            query,
            ("component:auth-service", "component:user-service", EdgeRel.DEPENDS_ON.value)
        )

        # Verify the edge exists
        self.assertEqual(len(result), 1)

        # Verify we can query across repositories
        self.arc.set_active_repositories([repo1_id, repo2_id])

        # This is a simplified test since we can't easily test the full query functionality
        # In a real scenario, we would use arc.query() or arc.get_related_entities()
        components = self.arc.adapter.get_nodes_by_type(NodeType.COMPONENT)
        self.assertEqual(len(components), 2)

    def test_error_handling(self):
        """Test error handling for repository operations."""
        from arc_memory.sdk.errors import QueryError

        # Since we're using a mock setup, adding a non-existent repository might not fail
        # Let's focus on the repository ID validation instead

        # Ensure a repository exists
        repo1_id = self.arc.ensure_repository(name="Repo 1")

        # Test setting an invalid repository as active
        with self.assertRaises(QueryError):
            self.arc.set_active_repositories(["invalid-repo-id"])

        # Test filtering by an invalid repository ID
        result = self.arc.adapter.get_nodes_by_type(NodeType.DOCUMENT, ["invalid-repo-id"])
        self.assertEqual(len(result), 0)  # Should return empty list, not error

    def test_edge_cases(self):
        """Test edge cases for multi-repository support."""
        # Clear any existing repositories from previous tests
        # This is a bit of a hack, but necessary for test isolation
        self.arc.adapter.conn.execute("DELETE FROM repositories")
        self.arc.adapter.conn.commit()
        self.arc.active_repos = []

        # Test with empty repository list
        repos = self.arc.list_repositories()
        self.assertEqual(len(repos), 0)

        # The get_active_repositories method automatically ensures the current repository
        # if no active repositories are set, so we need to test this behavior
        self.arc.set_active_repositories([])
        active_repos = self.arc.get_active_repositories()
        self.assertEqual(len(active_repos), 1)  # Should have one repository (the current one)

        # Test adding the same repository twice
        repo1_id = self.arc.ensure_repository(name="Repo 1")
        repo1_id_again = self.arc.ensure_repository(name="Repo 1 Again")

        # Should return the same ID
        self.assertEqual(repo1_id, repo1_id_again)

        # Repository list should still have only one entry
        repos = self.arc.list_repositories()
        self.assertEqual(len(repos), 1)

        # Test with special characters in repository name
        special_repo_id = self.arc.add_repository(self.repo2_path, name="Repo 2 !@#$%^&*()")
        repos = self.arc.list_repositories()
        repo_names = {repo["name"] for repo in repos}
        self.assertIn("Repo 2 !@#$%^&*()", repo_names)

        # Verify the special repo was added
        self.assertEqual(len(repos), 2)


if __name__ == "__main__":
    unittest.main()
