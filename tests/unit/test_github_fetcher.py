"""Unit tests for GitHub fetcher."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from arc_memory.errors import GitHubAuthError, IngestError
from arc_memory.ingest.github_fetcher import GitHubFetcher
from arc_memory.ingest.github_graphql import (
    PULL_REQUESTS_QUERY,
    ISSUES_QUERY,
    UPDATED_PRS_QUERY,
    UPDATED_ISSUES_QUERY,
)
from arc_memory.schema.models import Edge, EdgeRel, IssueNode, PRNode


@pytest.fixture
def mock_graphql_client():
    """Create a mock GraphQL client."""
    return MagicMock()


@pytest.fixture
def mock_rest_client():
    """Create a mock REST client."""
    return MagicMock()


@pytest.fixture
def github_fetcher(mock_graphql_client, mock_rest_client):
    """Create a GitHubFetcher with mock clients."""
    with patch("arc_memory.ingest.github_fetcher.GitHubGraphQLClient", return_value=mock_graphql_client), \
         patch("arc_memory.ingest.github_fetcher.GitHubRESTClient", return_value=mock_rest_client):
        fetcher = GitHubFetcher("test-token")
        return fetcher


class TestGitHubFetcher:
    """Tests for GitHubFetcher."""

    @pytest.mark.asyncio
    async def test_fetch_pull_requests(self, github_fetcher, mock_graphql_client):
        """Test fetching pull requests."""
        # Set up mock response
        mock_prs = [
            {"id": "PR_1", "number": 1, "title": "Test PR 1"},
            {"id": "PR_2", "number": 2, "title": "Test PR 2"},
        ]
        mock_graphql_client.paginate_query = AsyncMock(return_value=mock_prs)

        # Fetch PRs
        prs = await github_fetcher.fetch_pull_requests("test-owner", "test-repo")

        # Check results
        assert prs == mock_prs
        mock_graphql_client.paginate_query.assert_called_once()

        # Check that the function was called with the correct arguments
        mock_graphql_client.paginate_query.assert_called_once_with(
            PULL_REQUESTS_QUERY,  # Since parameter is None, we should use the regular query
            {"owner": "test-owner", "repo": "test-repo"},
            ["repository", "pullRequests"]
        )

    @pytest.mark.asyncio
    async def test_fetch_pull_requests_with_since(self, github_fetcher, mock_graphql_client):
        """Test fetching pull requests with since parameter."""
        # Set up mock response
        mock_prs = [
            {"id": "PR_1", "number": 1, "title": "Test PR 1", "updatedAt": "2023-01-02T00:00:00Z"},
        ]
        mock_graphql_client.paginate_query = AsyncMock(return_value=mock_prs)

        # Fetch PRs with since parameter
        since = datetime(2023, 1, 1)
        prs = await github_fetcher.fetch_pull_requests("test-owner", "test-repo", since)

        # Check results
        assert prs == mock_prs
        mock_graphql_client.paginate_query.assert_called_once()

        # Check that the function was called with the correct arguments
        mock_graphql_client.paginate_query.assert_called_once_with(
            UPDATED_PRS_QUERY,
            {"owner": "test-owner", "repo": "test-repo"},
            ["repository", "pullRequests"]
        )

    @pytest.mark.asyncio
    async def test_fetch_issues(self, github_fetcher, mock_graphql_client):
        """Test fetching issues."""
        # Set up mock response
        mock_issues = [
            {"id": "ISSUE_1", "number": 1, "title": "Test Issue 1"},
            {"id": "ISSUE_2", "number": 2, "title": "Test Issue 2"},
        ]
        mock_graphql_client.paginate_query = AsyncMock(return_value=mock_issues)

        # Fetch issues
        issues = await github_fetcher.fetch_issues("test-owner", "test-repo")

        # Check results
        assert issues == mock_issues
        mock_graphql_client.paginate_query.assert_called_once()

        # Check that the function was called with the correct arguments
        mock_graphql_client.paginate_query.assert_called_once_with(
            ISSUES_QUERY,
            {"owner": "test-owner", "repo": "test-repo"},
            ["repository", "issues"]
        )

    @pytest.mark.asyncio
    async def test_fetch_issues_with_since(self, github_fetcher, mock_graphql_client):
        """Test fetching issues with since parameter."""
        # Set up mock response
        mock_issues = [
            {"id": "ISSUE_1", "number": 1, "title": "Test Issue 1", "updatedAt": "2023-01-02T00:00:00Z"},
        ]
        mock_graphql_client.paginate_query = AsyncMock(return_value=mock_issues)

        # Fetch issues with since parameter
        since = datetime(2023, 1, 1)
        issues = await github_fetcher.fetch_issues("test-owner", "test-repo", since)

        # Check results
        assert issues == mock_issues
        mock_graphql_client.paginate_query.assert_called_once()

        # Check that the function was called with the correct arguments
        mock_graphql_client.paginate_query.assert_called_once_with(
            UPDATED_ISSUES_QUERY,
            {"owner": "test-owner", "repo": "test-repo"},
            ["repository", "issues"]
        )

    @pytest.mark.asyncio
    async def test_fetch_pr_details(self, github_fetcher, mock_rest_client):
        """Test fetching PR details."""
        # Set up mock responses
        mock_rest_client.get_pr_files.return_value = [
            {"filename": "file1.py", "additions": 10, "deletions": 5},
        ]
        mock_rest_client.get_pr_reviews.return_value = [
            {"id": 1, "user": {"login": "reviewer1"}, "state": "APPROVED"},
        ]
        mock_rest_client.get_pr_comments.return_value = [
            {"id": 1, "user": {"login": "user1"}, "body": "Comment 1"},
        ]

        # Fetch PR details
        details = await github_fetcher.fetch_pr_details("test-owner", "test-repo", 1)

        # Check results
        assert "files" in details
        assert "reviews" in details
        assert "comments" in details
        assert len(details["files"]) == 1
        assert len(details["reviews"]) == 1
        assert len(details["comments"]) == 1
        mock_rest_client.get_pr_files.assert_called_once_with("test-owner", "test-repo", 1)
        mock_rest_client.get_pr_reviews.assert_called_once_with("test-owner", "test-repo", 1)
        mock_rest_client.get_pr_comments.assert_called_once_with("test-owner", "test-repo", 1)

    @pytest.mark.asyncio
    async def test_fetch_issue_details(self, github_fetcher, mock_rest_client):
        """Test fetching issue details."""
        # Set up mock response
        mock_rest_client.get_issue_comments.return_value = [
            {"id": 1, "user": {"login": "user1"}, "body": "Comment 1"},
        ]

        # Fetch issue details
        details = await github_fetcher.fetch_issue_details("test-owner", "test-repo", 1)

        # Check results
        assert "comments" in details
        assert len(details["comments"]) == 1
        mock_rest_client.get_issue_comments.assert_called_once_with("test-owner", "test-repo", 1)

    def test_create_pr_node(self, github_fetcher):
        """Test creating a PR node."""
        # Create PR data
        pr_data = {
            "id": "PR_1",
            "number": 1,
            "title": "Test PR",
            "body": "This is a test PR",
            "state": "OPEN",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-02T00:00:00Z",
            "closedAt": None,
            "mergedAt": None,
            "author": {"login": "test-user"},
            "baseRefName": "main",
            "headRefName": "feature-branch",
            "url": "https://github.com/test-owner/test-repo/pull/1",
            "mergeCommit": None,
        }

        # Create PR details
        pr_details = {
            "files": [
                {"filename": "file1.py", "additions": 10, "deletions": 5, "changes": 15},
            ],
            "reviews": [
                {"user": {"login": "reviewer1"}, "state": "APPROVED", "body": "LGTM", "submitted_at": "2023-01-02T00:00:00Z"},
            ],
            "comments": [
                {"user": {"login": "user1"}, "body": "Comment 1", "created_at": "2023-01-02T00:00:00Z"},
            ],
        }

        # Create PR node
        pr_node = github_fetcher.create_pr_node(pr_data, pr_details)

        # Check node
        assert isinstance(pr_node, PRNode)
        assert pr_node.id == "PR_1"
        assert pr_node.number == 1
        assert pr_node.title == "Test PR"
        assert pr_node.body == "This is a test PR"
        assert pr_node.state == "OPEN"
        assert pr_node.merged_at is None
        assert pr_node.merged_commit_sha is None
        assert pr_node.url == "https://github.com/test-owner/test-repo/pull/1"

        # Check extra data
        assert pr_node.extra["author"] == "test-user"
        assert pr_node.extra["baseRefName"] == "main"
        assert pr_node.extra["headRefName"] == "feature-branch"
        assert len(pr_node.extra["files"]) == 1
        assert len(pr_node.extra["reviews"]) == 1
        assert len(pr_node.extra["comments"]) == 1

    def test_create_issue_node(self, github_fetcher):
        """Test creating an issue node."""
        # Create issue data
        issue_data = {
            "id": "ISSUE_1",
            "number": 1,
            "title": "Test Issue",
            "body": "This is a test issue",
            "state": "OPEN",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-02T00:00:00Z",
            "closedAt": None,
            "author": {"login": "test-user"},
            "url": "https://github.com/test-owner/test-repo/issues/1",
            "labels": {"nodes": [{"name": "bug"}, {"name": "enhancement"}]},
        }

        # Create issue details
        issue_details = {
            "comments": [
                {"user": {"login": "user1"}, "body": "Comment 1", "created_at": "2023-01-02T00:00:00Z"},
            ],
        }

        # Create issue node
        issue_node = github_fetcher.create_issue_node(issue_data, issue_details)

        # Check node
        assert isinstance(issue_node, IssueNode)
        assert issue_node.id == "ISSUE_1"
        assert issue_node.number == 1
        assert issue_node.title == "Test Issue"
        assert issue_node.body == "This is a test issue"
        assert issue_node.state == "OPEN"
        assert issue_node.closed_at is None
        assert issue_node.url == "https://github.com/test-owner/test-repo/issues/1"
        assert set(issue_node.labels) == {"bug", "enhancement"}

        # Check extra data
        assert issue_node.extra["author"] == "test-user"
        assert len(issue_node.extra["comments"]) == 1

    def test_extract_mentions(self, github_fetcher):
        """Test extracting mentions from text."""
        # Test with various mention types
        text = """
        This is a test with @username mentions and #123 issue references.
        It also has multiple mentions like @another-user and #456.
        """

        mentions = github_fetcher.extract_mentions(text)

        # Check mentions
        assert "username" in mentions
        assert "another-user" in mentions
        assert "#123" in mentions
        assert "#456" in mentions

    def test_create_mention_edges(self, github_fetcher):
        """Test creating mention edges."""
        # Create test data
        source_id = "PR_1"
        text = "This PR fixes #2 and relates to #3. cc @username"

        repo_issues = [
            {"id": "ISSUE_2", "number": 2},
            {"id": "ISSUE_3", "number": 3},
        ]

        repo_prs = [
            {"id": "PR_1", "number": 1},
            {"id": "PR_4", "number": 4},
        ]

        # Create mention edges
        edges = github_fetcher.create_mention_edges(source_id, text, repo_issues, repo_prs)

        # Check edges
        assert len(edges) == 2  # Should have edges for #2 and #3

        # Check edge properties
        for edge in edges:
            assert edge.src == "PR_1"
            assert edge.rel == EdgeRel.MENTIONS
            assert edge.dst in ["ISSUE_2", "ISSUE_3"]
            assert edge.properties["type"] == "issue_reference"

    def test_fetch_pull_requests_sync(self, github_fetcher):
        """Test synchronous wrapper for fetch_pull_requests."""
        # Mock the async method
        mock_prs = [{"id": "PR_1", "number": 1}]
        github_fetcher.fetch_pull_requests = AsyncMock(return_value=mock_prs)

        # Call the sync wrapper
        prs = github_fetcher.fetch_pull_requests_sync("test-owner", "test-repo")

        # Check results
        assert prs == mock_prs
        github_fetcher.fetch_pull_requests.assert_called_once_with("test-owner", "test-repo", None)

    def test_fetch_issues_sync(self, github_fetcher):
        """Test synchronous wrapper for fetch_issues."""
        # Mock the async method
        mock_issues = [{"id": "ISSUE_1", "number": 1}]
        github_fetcher.fetch_issues = AsyncMock(return_value=mock_issues)

        # Call the sync wrapper
        issues = github_fetcher.fetch_issues_sync("test-owner", "test-repo")

        # Check results
        assert issues == mock_issues
        github_fetcher.fetch_issues.assert_called_once_with("test-owner", "test-repo", None)

    def test_fetch_pr_details_sync(self, github_fetcher):
        """Test synchronous wrapper for fetch_pr_details."""
        # Mock the async method
        mock_details = {"files": [], "reviews": [], "comments": []}
        github_fetcher.fetch_pr_details = AsyncMock(return_value=mock_details)

        # Call the sync wrapper
        details = github_fetcher.fetch_pr_details_sync("test-owner", "test-repo", 1)

        # Check results
        assert details == mock_details
        github_fetcher.fetch_pr_details.assert_called_once_with("test-owner", "test-repo", 1)

    def test_fetch_issue_details_sync(self, github_fetcher):
        """Test synchronous wrapper for fetch_issue_details."""
        # Mock the async method
        mock_details = {"comments": []}
        github_fetcher.fetch_issue_details = AsyncMock(return_value=mock_details)

        # Call the sync wrapper
        details = github_fetcher.fetch_issue_details_sync("test-owner", "test-repo", 1)

        # Check results
        assert details == mock_details
        github_fetcher.fetch_issue_details.assert_called_once_with("test-owner", "test-repo", 1)
