"""Integration tests for GitHub incremental build support.

These tests require a valid GitHub token to be set in the environment variable GITHUB_TOKEN.
They test the incremental build functionality with real API calls.
"""

import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from arc_memory.ingest.github import GitHubIngestor
from arc_memory.ingest.github_fetcher import GitHubFetcher


# Skip all tests if GITHUB_TOKEN is not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN environment variable not set",
)


@pytest.fixture
def github_token():
    """Get the GitHub token from the environment."""
    return os.environ.get("GITHUB_TOKEN")


@pytest.fixture
def github_ingestor():
    """Create a GitHub ingestor."""
    return GitHubIngestor()


@pytest.fixture
def github_fetcher(github_token):
    """Create a GitHub fetcher with the GitHub token."""
    return GitHubFetcher(github_token)


@pytest.fixture
def test_repo():
    """Get the test repository information."""
    return {
        "owner": "Arc-Computer",
        "repo": "arc-memory",
        "path": os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
    }


class TestIncrementalBuild:
    """Tests for incremental build support."""

    def test_incremental_build_with_timestamp(self, github_ingestor, github_token, test_repo):
        """Test incremental build with a timestamp."""
        # Set up last processed data with a timestamp 7 days ago
        last_processed = {
            "timestamp": (datetime.now() - timedelta(days=7)).isoformat(),
        }

        # Perform an incremental build
        nodes, edges, metadata = github_ingestor.ingest(
            repo_path=test_repo["path"],
            token=github_token,
            last_processed=last_processed,
        )

        # Check that we got some data
        assert "timestamp" in metadata
        assert datetime.fromisoformat(metadata["timestamp"]) >= datetime.fromisoformat(last_processed["timestamp"])

        # The test is successful if we don't get any errors
        assert "error" not in metadata

    def test_incremental_build_with_recent_timestamp(self, github_ingestor, github_token, test_repo):
        """Test incremental build with a very recent timestamp."""
        # Set up last processed data with a timestamp 1 minute ago
        last_processed = {
            "timestamp": (datetime.now() - timedelta(minutes=1)).isoformat(),
        }

        # Perform an incremental build
        nodes, edges, metadata = github_ingestor.ingest(
            repo_path=test_repo["path"],
            token=github_token,
            last_processed=last_processed,
        )

        # Check that we got some data
        assert "timestamp" in metadata
        assert datetime.fromisoformat(metadata["timestamp"]) >= datetime.fromisoformat(last_processed["timestamp"])

        # The test is successful if we don't get any errors
        assert "error" not in metadata

    def test_incremental_build_with_future_timestamp(self, github_ingestor, github_token, test_repo):
        """Test incremental build with a future timestamp."""
        # Set up last processed data with a timestamp 1 day in the future
        last_processed = {
            "timestamp": (datetime.now() + timedelta(days=1)).isoformat(),
        }

        # Perform an incremental build
        nodes, edges, metadata = github_ingestor.ingest(
            repo_path=test_repo["path"],
            token=github_token,
            last_processed=last_processed,
        )

        # Check that we got some data
        assert "timestamp" in metadata

        # We should still get a valid timestamp even if the input was in the future
        assert datetime.fromisoformat(metadata["timestamp"]) >= datetime.now() - timedelta(minutes=5)

        # The test is successful if we don't get any errors
        assert "error" not in metadata

    def test_fetch_updated_prs(self, github_fetcher, test_repo):
        """Test fetching updated PRs."""
        # Set up a timestamp 7 days ago
        since = datetime.now() - timedelta(days=7)

        # Fetch updated PRs
        prs = github_fetcher.fetch_pull_requests_sync(
            test_repo["owner"],
            test_repo["repo"],
            since,
        )

        # Check the results
        assert isinstance(prs, list)

        # If we have PRs, check that they were updated after the since timestamp
        for pr in prs:
            updated_at = datetime.fromisoformat(pr["updatedAt"].replace("Z", "+00:00"))
            # Ensure since is timezone-aware for comparison
            if since.tzinfo is None:
                since_aware = since.replace(tzinfo=timezone.utc)
            else:
                since_aware = since
            assert updated_at >= since_aware

    def test_fetch_updated_issues(self, github_fetcher, test_repo):
        """Test fetching updated issues."""
        # Set up a timestamp 7 days ago
        since = datetime.now() - timedelta(days=7)

        # Fetch updated issues
        issues = github_fetcher.fetch_issues_sync(
            test_repo["owner"],
            test_repo["repo"],
            since,
        )

        # Check the results
        assert isinstance(issues, list)

        # If we have issues, check that they were updated after the since timestamp
        for issue in issues:
            updated_at = datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00"))
            # Ensure since is timezone-aware for comparison
            if since.tzinfo is None:
                since_aware = since.replace(tzinfo=timezone.utc)
            else:
                since_aware = since
            assert updated_at >= since_aware

    def test_full_incremental_build_cycle(self, github_ingestor, github_token, test_repo):
        """Test a full incremental build cycle."""
        # First, do a full build
        nodes1, edges1, metadata1 = github_ingestor.ingest(
            repo_path=test_repo["path"],
            token=github_token,
            last_processed=None,
        )

        # Check that we got some data
        assert "timestamp" in metadata1
        assert len(nodes1) >= 0
        assert len(edges1) >= 0

        # Now, do an incremental build using the metadata from the first build
        nodes2, edges2, metadata2 = github_ingestor.ingest(
            repo_path=test_repo["path"],
            token=github_token,
            last_processed=metadata1,
        )

        # Check that we got some data
        assert "timestamp" in metadata2
        assert datetime.fromisoformat(metadata2["timestamp"]) >= datetime.fromisoformat(metadata1["timestamp"])

        # The second build should have fewer nodes and edges (or the same number)
        # since we're only fetching updates
        assert len(nodes2) <= len(nodes1)
        assert len(edges2) <= len(edges1)

        # The test is successful if we don't get any errors
        assert "error" not in metadata2
