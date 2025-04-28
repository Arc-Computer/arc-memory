"""Unit tests for GitHub ingestor."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from arc_memory.ingest.github import GitHubIngestor
from arc_memory.schema.models import IssueNode, PRNode


@pytest.fixture
def mock_repo():
    """Create a mock Git repository."""
    repo = MagicMock()
    repo.working_dir = "/test/repo"
    repo.remotes.origin.url = "https://github.com/test-owner/test-repo.git"
    return repo


@pytest.fixture
def github_ingestor(mock_repo):
    """Create a GitHubIngestor with a mock repository."""
    with patch("arc_memory.ingest.github.Repo", return_value=mock_repo):
        ingestor = GitHubIngestor()
        return ingestor


class TestGitHubIngestor:
    """Tests for GitHubIngestor."""

    def test_ingest_with_no_token(self, github_ingestor):
        """Test ingesting GitHub data with no token."""
        # Mock the token functions to return None
        with patch("arc_memory.ingest.github.get_github_token", return_value=None), \
             patch("arc_memory.ingest.github.get_installation_token_for_repo", return_value=None), \
             patch("arc_memory.ingest.github.get_repo_info", return_value=("test-owner", "test-repo")):

            # Call the ingest method
            nodes, edges, metadata = github_ingestor.ingest(
                repo_path="/test/repo",
                last_processed=None,
            )

            # Check that no data was ingested
            assert len(nodes) == 0
            assert len(edges) == 0
            assert "error" in metadata
            assert "No GitHub token found" in metadata["error"]

    def test_ingest_with_github_token(self, github_ingestor):
        """Test ingesting GitHub data with a GitHub token."""
        # Mock the token functions
        with patch("arc_memory.ingest.github.get_github_token", return_value="test-token"), \
             patch("arc_memory.ingest.github.get_installation_token_for_repo", return_value=None), \
             patch("arc_memory.ingest.github.get_repo_info", return_value=("test-owner", "test-repo")):

            # Create mock PR and issue nodes
            mock_pr_node = PRNode(
                id="PR_1",
                title="Test PR",
                body="This is a test PR",
                ts=datetime(2023, 1, 1),
                number=1,
                state="OPEN",
                merged_at=None,
                merged_by=None,
                merged_commit_sha=None,
                url="https://github.com/test-owner/test-repo/pull/1",
                extra={},
            )

            mock_issue_node = IssueNode(
                id="ISSUE_1",
                title="Test Issue",
                body="This is a test issue",
                ts=datetime(2023, 1, 1),
                number=1,
                state="OPEN",
                closed_at=None,
                labels=["bug"],
                url="https://github.com/test-owner/test-repo/issues/1",
                extra={},
            )

            # Mock the GitHubFetcher
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_pull_requests_sync.return_value = [{"id": "PR_1", "number": 1}]
            mock_fetcher.fetch_issues_sync.return_value = [{"id": "ISSUE_1", "number": 1}]
            mock_fetcher.fetch_pr_details_sync.return_value = {"files": [], "reviews": [], "comments": []}
            mock_fetcher.fetch_issue_details_sync.return_value = {"comments": []}
            mock_fetcher.create_pr_node.return_value = mock_pr_node
            mock_fetcher.create_issue_node.return_value = mock_issue_node
            mock_fetcher.create_mention_edges.return_value = []

            # Patch the GitHubFetcher import
            with patch("arc_memory.ingest.github_fetcher.GitHubFetcher", return_value=mock_fetcher):
                # Call the ingest method
                nodes, edges, metadata = github_ingestor.ingest(
                    repo_path="/test/repo",
                    token="test-token",
                    last_processed=None,
                )

                # Check results
                assert len(nodes) == 2
                assert any(isinstance(node, PRNode) for node in nodes)
                assert any(isinstance(node, IssueNode) for node in nodes)

                # Check that the fetcher methods were called
                mock_fetcher.fetch_pull_requests_sync.assert_called_once_with("test-owner", "test-repo", None)
                mock_fetcher.fetch_issues_sync.assert_called_once_with("test-owner", "test-repo", None)
                mock_fetcher.fetch_pr_details_sync.assert_called_once_with("test-owner", "test-repo", 1)
                mock_fetcher.fetch_issue_details_sync.assert_called_once_with("test-owner", "test-repo", 1)

    def test_ingest_with_incremental_build(self, github_ingestor):
        """Test ingesting GitHub data with incremental build."""
        # Mock the token functions
        with patch("arc_memory.ingest.github.get_github_token", return_value="test-token"), \
             patch("arc_memory.ingest.github.get_installation_token_for_repo", return_value=None), \
             patch("arc_memory.ingest.github.get_repo_info", return_value=("test-owner", "test-repo")):

            # Set up last processed data
            last_processed = {
                "timestamp": "2023-01-01T00:00:00Z",
            }

            # Mock the GitHubFetcher
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_pull_requests_sync.return_value = []
            mock_fetcher.fetch_issues_sync.return_value = []

            # Patch the GitHubFetcher import
            with patch("arc_memory.ingest.github_fetcher.GitHubFetcher", return_value=mock_fetcher):
                # Call the ingest method
                github_ingestor.ingest(
                    repo_path="/test/repo",
                    token="test-token",
                    last_processed=last_processed,
                )

                # Check that the fetcher was called with the since parameter
                since = datetime.fromisoformat("2023-01-01T00:00:00Z")
                mock_fetcher.fetch_pull_requests_sync.assert_called_once()
                call_args = mock_fetcher.fetch_pull_requests_sync.call_args[0]
                assert call_args[0] == "test-owner"
                assert call_args[1] == "test-repo"
                assert call_args[2].isoformat() == since.isoformat()

    def test_ingest_with_installation_token(self, github_ingestor):
        """Test ingesting GitHub data with installation token."""
        # Mock the token functions
        with patch("arc_memory.ingest.github.get_github_token", return_value=None), \
             patch("arc_memory.ingest.github.get_installation_token_for_repo", return_value="installation-token"), \
             patch("arc_memory.ingest.github.get_repo_info", return_value=("test-owner", "test-repo")):

            # Mock the GitHubFetcher
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_pull_requests_sync.return_value = []
            mock_fetcher.fetch_issues_sync.return_value = []

            # Patch the GitHubFetcher import
            with patch("arc_memory.ingest.github_fetcher.GitHubFetcher", return_value=mock_fetcher):
                # Call the ingest method
                github_ingestor.ingest(
                    repo_path="/test/repo",
                    last_processed=None,
                )

                # Check that the fetcher was created with the installation token
                # We can't directly check the token value since it's passed to the constructor
                # but we can verify that the fetcher was called
                mock_fetcher.fetch_pull_requests_sync.assert_called_once_with("test-owner", "test-repo", None)
