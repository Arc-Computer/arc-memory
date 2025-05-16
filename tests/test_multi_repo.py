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


if __name__ == "__main__":
    unittest.main()
