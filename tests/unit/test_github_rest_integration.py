"""Integration tests for GitHub REST client."""

import os
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from arc_memory.errors import GitHubAuthError, IngestError
from arc_memory.ingest.github_rest import GitHubRESTClient


@pytest.mark.skipif(
    not os.environ.get("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN environment variable not set",
)
class TestGitHubRESTIntegration:
    """Integration tests for the GitHub REST client.

    These tests require a valid GitHub token in the GITHUB_TOKEN environment variable.
    They are skipped if the token is not set.
    """

    @pytest.fixture
    def rest_client(self):
        """Create a GitHubRESTClient with a real token."""
        token = os.environ.get("GITHUB_TOKEN")
        return GitHubRESTClient(token)

    def test_rate_limit_info(self, rest_client):
        """Test getting rate limit info."""
        # Update rate limit info
        rest_client._update_rate_limit_info()

        # Check that we got rate limit info
        assert rest_client.rate_limit_remaining is not None
        assert rest_client.rate_limit_limit is not None
        assert rest_client.rate_limit_reset is not None

        # Check that the rate limit is reasonable
        assert rest_client.rate_limit_limit > 0
        assert rest_client.rate_limit_remaining >= 0
        assert rest_client.rate_limit_remaining <= rest_client.rate_limit_limit

    def test_batch_request(self, rest_client):
        """Test batch requests."""
        # Use known endpoints from a public repository
        owner = "Arc-Computer"
        repo = "arc-memory"
        endpoints = [
            f"/repos/{owner}/{repo}/pulls/1",
            f"/repos/{owner}/{repo}/issues/1",
        ]

        # Make a batch request
        results = rest_client.batch_request("GET", endpoints)

        # Check that we got results
        assert isinstance(results, list)
        assert len(results) == len(endpoints)

        # Check that each result is a dictionary or None
        for result in results:
            assert result is None or isinstance(result, dict)

    def test_get_commits_for_pr(self, rest_client):
        """Test getting commits for a PR."""
        # Use a known PR from a public repository
        owner = "Arc-Computer"
        repo = "arc-memory"
        pr_number = 11  # Use a PR that exists in the repository

        try:
            # Get commits for PR
            commits = rest_client.get_commits_for_pr(owner, repo, pr_number)

            # Check that we got commits
            assert isinstance(commits, list)

            # If there are commits, check that they have the expected fields
            for commit in commits:
                assert "sha" in commit
                assert "commit" in commit
                assert "message" in commit["commit"]
        except Exception as e:
            # Skip the test if the PR doesn't exist or we can't access it
            if "404" in str(e):
                pytest.skip(f"PR {pr_number} not found or not accessible")

    def test_get_review_comments(self, rest_client):
        """Test getting review comments for a PR."""
        # Use a known PR from a public repository
        owner = "Arc-Computer"
        repo = "arc-memory"
        pr_number = 11  # Use a PR that exists in the repository

        try:
            # Get review comments
            comments = rest_client.get_review_comments(owner, repo, pr_number)

            # Check that we got comments
            assert isinstance(comments, list)

            # If there are comments, check that they have the expected fields
            for comment in comments:
                if comment:  # Some comments might be None
                    assert "id" in comment
                    assert "user" in comment
                    assert "body" in comment
        except Exception as e:
            # Skip the test if the PR doesn't exist or we can't access it
            if "404" in str(e):
                pytest.skip(f"PR {pr_number} not found or not accessible")

    def test_get_issue_events(self, rest_client):
        """Test getting events for an issue."""
        # Use a known issue from a public repository
        owner = "Arc-Computer"
        repo = "arc-memory"
        issue_number = 11  # Use an issue that exists in the repository

        # Get issue events
        events = rest_client.get_issue_events(owner, repo, issue_number)

        # Check that we got events
        assert isinstance(events, list)

        # If there are events, check that they have the expected fields
        for event in events:
            if event:  # Some events might be None
                assert "event" in event

    def test_get_issue_timeline(self, rest_client):
        """Test getting issue timeline."""
        # Use a known issue from a public repository
        owner = "Arc-Computer"
        repo = "arc-memory"
        issue_number = 11  # Use an issue that exists in the repository

        # Get issue timeline
        timeline = rest_client.get_issue_timeline(owner, repo, issue_number)

        # Check that we got timeline events
        assert isinstance(timeline, list)

        # If there are timeline events, check that they have the expected fields
        for event in timeline:
            if event:  # Some events might be None
                assert "event" in event or "body" in event  # Timeline can include comments

    def test_get_pr_details_batch(self, rest_client):
        """Test getting PR details in batch."""
        # Use known PRs from a public repository
        owner = "Arc-Computer"
        repo = "arc-memory"
        pr_numbers = [11, 12]  # Use PRs that exist in the repository

        # Get PR details in batch
        details = rest_client.get_pr_details_batch(owner, repo, pr_numbers)

        # Check that we got details
        assert isinstance(details, list)
        assert len(details) == len(pr_numbers)

        # Check that each detail is a dictionary or None
        for detail in details:
            assert detail is None or isinstance(detail, dict)
            if detail:
                assert "number" in detail
                assert "title" in detail
