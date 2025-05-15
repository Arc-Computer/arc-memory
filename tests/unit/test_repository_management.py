"""Tests for repository management methods in the SDK."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from arc_memory.sdk import Arc
from arc_memory.sdk.errors import SDKError, AdapterError, QueryError
from arc_memory.schema.models import RepositoryNode, NodeType


class TestRepositoryManagement(unittest.TestCase):
    """Tests for repository management methods in the SDK."""

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

        # Create a .git directory to make it look like a real repository
        git_dir = self.repo_path / ".git"
        git_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        self.get_adapter_patcher.stop()
        self.get_db_path_patcher.stop()
        self.temp_dir.cleanup()

    def test_get_current_repository_none(self):
        """Test getting the current repository when it doesn't exist."""
        # Set up the mock adapter to return None
        self.mock_adapter.conn = MagicMock()
        self.mock_adapter.conn.execute.return_value.fetchone.return_value = None

        # Create an Arc instance and call get_current_repository
        arc = Arc(repo_path=self.repo_path)
        repo = arc.get_current_repository()

        # Verify that the adapter's execute method was called with the correct query
        self.mock_adapter.conn.execute.assert_called_with(
            unittest.mock.ANY,  # We don't care about the exact SQL query
            (str(self.repo_path.absolute()),)
        )

        # Verify that the result is None
        self.assertIsNone(repo)

    def test_get_current_repository_exists(self):
        """Test getting the current repository when it exists."""
        # Set up the mock adapter to return a repository
        self.mock_adapter.conn = MagicMock()
        mock_row = {
            "id": "repository:test-repo",
            "name": "test-repo",
            "url": "https://github.com/test-org/test-repo",
            "local_path": str(self.repo_path.absolute()),
            "default_branch": "main",
            "metadata": '{"description": "A test repository"}'
        }
        self.mock_adapter.conn.execute.return_value.fetchone.return_value = mock_row

        # Create an Arc instance and call get_current_repository
        arc = Arc(repo_path=self.repo_path)
        repo = arc.get_current_repository()

        # Verify that the adapter's execute method was called with the correct query
        self.mock_adapter.conn.execute.assert_called_with(
            unittest.mock.ANY,  # We don't care about the exact SQL query
            (str(self.repo_path.absolute()),)
        )

        # Verify that the result is correct
        self.assertIsNotNone(repo)
        self.assertEqual(repo["id"], "repository:test-repo")
        self.assertEqual(repo["name"], "test-repo")
        self.assertEqual(repo["url"], "https://github.com/test-org/test-repo")
        self.assertEqual(repo["local_path"], str(self.repo_path.absolute()))
        self.assertEqual(repo["default_branch"], "main")
        self.assertEqual(repo["metadata"], {"description": "A test repository"})

    @patch("subprocess.run")
    def test_ensure_repository_new(self, mock_run):
        """Test ensuring a repository when it doesn't exist."""
        # Set up the mock adapter to return None for get_current_repository
        self.mock_adapter.conn = MagicMock()
        self.mock_adapter.conn.execute.return_value.fetchone.return_value = None

        # Set up the mock subprocess.run to return git info
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="https://github.com/test-org/test-repo\n"),
            MagicMock(returncode=0, stdout="main\n")
        ]

        # Create an Arc instance and call ensure_repository
        arc = Arc(repo_path=self.repo_path)
        repo_id = arc.ensure_repository()

        # Verify that the adapter's add_nodes_and_edges method was called
        self.mock_adapter.add_nodes_and_edges.assert_called_once()

        # Get the repository node that was created
        args, _ = self.mock_adapter.add_nodes_and_edges.call_args
        nodes, edges = args

        # Verify that a repository node was created
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], RepositoryNode)
        self.assertEqual(nodes[0].type, NodeType.REPOSITORY)
        self.assertEqual(nodes[0].name, self.repo_path.name)
        self.assertEqual(nodes[0].url, "https://github.com/test-org/test-repo")
        self.assertEqual(nodes[0].local_path, str(self.repo_path.absolute()))
        self.assertEqual(nodes[0].default_branch, "main")

        # Verify that the repository ID was returned
        self.assertEqual(repo_id, nodes[0].id)

        # Verify that the current_repo_id was set
        self.assertEqual(arc.current_repo_id, repo_id)

    def test_ensure_repository_existing(self):
        """Test ensuring a repository when it already exists."""
        # Set up the mock adapter to return a repository for get_current_repository
        self.mock_adapter.conn = MagicMock()
        mock_row = {
            "id": "repository:test-repo",
            "name": "test-repo",
            "url": "https://github.com/test-org/test-repo",
            "local_path": str(self.repo_path.absolute()),
            "default_branch": "main",
            "metadata": '{"description": "A test repository"}'
        }
        self.mock_adapter.conn.execute.return_value.fetchone.return_value = mock_row

        # Create an Arc instance and call ensure_repository
        arc = Arc(repo_path=self.repo_path)
        repo_id = arc.ensure_repository()

        # Verify that the adapter's add_nodes_and_edges method was not called
        self.mock_adapter.add_nodes_and_edges.assert_not_called()

        # Verify that the repository ID was returned
        self.assertEqual(repo_id, "repository:test-repo")

        # Verify that the current_repo_id was set
        self.assertEqual(arc.current_repo_id, "repository:test-repo")


if __name__ == "__main__":
    unittest.main()
