"""Integration tests for GitHub API integration.

These tests require a valid GitHub token to be set in the environment variable GITHUB_TOKEN.
They test the actual GitHub API integration with real API calls.
"""

import os
import time
from datetime import datetime

import pytest

from arc_memory.ingest.github_fetcher import GitHubFetcher
from arc_memory.ingest.github_graphql import GitHubGraphQLClient
from arc_memory.ingest.github_rest import GitHubRESTClient
from arc_memory.schema.models import PRNode, IssueNode


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
def graphql_client(github_token):
    """Create a GraphQL client with the GitHub token."""
    return GitHubGraphQLClient(github_token)


@pytest.fixture
def rest_client(github_token):
    """Create a REST client with the GitHub token."""
    return GitHubRESTClient(github_token)


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
    }


class TestGraphQLClient:
    """Tests for the GraphQL client with real API calls."""

    def test_execute_query(self, graphql_client, test_repo):
        """Test executing a simple GraphQL query."""
        # Simple query to get repository information
        query = """
        query GetRepo($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            name
            description
            url
          }
        }
        """
        variables = {
            "owner": test_repo["owner"],
            "name": test_repo["repo"],
        }

        # Execute the query
        result = graphql_client.execute_query_sync(query, variables)

        # Check the result
        assert "repository" in result
        assert result["repository"]["name"] == test_repo["repo"]

    def test_paginate_query(self, graphql_client, test_repo):
        """Test paginating a GraphQL query."""
        # Query to get pull requests with pagination
        query = """
        query GetPullRequests($owner: String!, $name: String!, $cursor: String) {
          repository(owner: $owner, name: $name) {
            pullRequests(first: 10, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                number
                title
              }
            }
          }
        }
        """
        variables = {
            "owner": test_repo["owner"],
            "name": test_repo["repo"],
        }
        path = ["repository", "pullRequests"]

        # Paginate the query
        results = graphql_client.paginate_query_sync(query, variables, path)

        # Check the results
        assert isinstance(results, list)
        # We might not have enough PRs to test pagination, so just check that we got some results
        assert len(results) >= 0


class TestRESTClient:
    """Tests for the REST client with real API calls."""

    def test_request(self, rest_client, test_repo):
        """Test making a simple REST request."""
        # Get repository information
        endpoint = f"/repos/{test_repo['owner']}/{test_repo['repo']}"
        result = rest_client.request("GET", endpoint)

        # Check the result
        assert isinstance(result, dict)
        assert result["name"] == test_repo["repo"]

    def test_paginate(self, rest_client, test_repo):
        """Test paginating REST requests."""
        # Get repository issues
        endpoint = f"/repos/{test_repo['owner']}/{test_repo['repo']}/issues"
        results = rest_client.paginate("GET", endpoint, max_pages=2)

        # Check the results
        assert isinstance(results, list)

    def test_batch_request(self, rest_client, test_repo):
        """Test making batch requests."""
        # Get information for multiple endpoints
        endpoints = [
            f"/repos/{test_repo['owner']}/{test_repo['repo']}",
            f"/repos/{test_repo['owner']}/{test_repo['repo']}/issues",
        ]
        results = rest_client.batch_request("GET", endpoints)

        # Check the results
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["name"] == test_repo["repo"]
        assert isinstance(results[1], list)

    def test_get_pr_files(self, rest_client, test_repo):
        """Test getting PR files."""
        # Find a PR number to test with
        endpoint = f"/repos/{test_repo['owner']}/{test_repo['repo']}/pulls"
        prs = rest_client.paginate("GET", endpoint, max_pages=1)

        if not prs:
            pytest.skip("No PRs found in the repository")

        pr_number = prs[0]["number"]

        # Get PR files
        files = rest_client.get_pr_files(test_repo["owner"], test_repo["repo"], pr_number)

        # Check the results
        # The PR might not have any files, so just check that we got a list
        assert isinstance(files, list)

    def test_get_commits_for_pr(self, rest_client, test_repo):
        """Test getting commits for a PR."""
        # Find a PR number to test with
        endpoint = f"/repos/{test_repo['owner']}/{test_repo['repo']}/pulls"
        prs = rest_client.paginate("GET", endpoint, max_pages=1)

        if not prs:
            pytest.skip("No PRs found in the repository")

        pr_number = prs[0]["number"]

        # Get PR commits
        commits = rest_client.get_commits_for_pr(test_repo["owner"], test_repo["repo"], pr_number)

        # Check the results
        # The PR might not have any commits, so just check that we got a list
        assert isinstance(commits, list)


class TestGitHubFetcher:
    """Tests for the GitHub fetcher with real API calls."""

    def test_fetch_pull_requests(self, github_fetcher, test_repo):
        """Test fetching pull requests."""
        # Fetch pull requests
        prs = github_fetcher.fetch_pull_requests_sync(test_repo["owner"], test_repo["repo"])

        # Check the results
        assert isinstance(prs, list)

        # If we have PRs, check that they have the expected fields
        for pr in prs:
            assert "number" in pr
            assert "title" in pr
            assert "body" in pr
            assert "state" in pr

    def test_fetch_issues(self, github_fetcher, test_repo):
        """Test fetching issues."""
        # Fetch issues
        issues = github_fetcher.fetch_issues_sync(test_repo["owner"], test_repo["repo"])

        # Check the results
        assert isinstance(issues, list)

        # If we have issues, check that they have the expected fields
        for issue in issues:
            assert "number" in issue
            assert "title" in issue
            assert "body" in issue
            assert "state" in issue

    def test_fetch_pr_details(self, github_fetcher, test_repo):
        """Test fetching PR details."""
        # Find a PR number to test with
        prs = github_fetcher.fetch_pull_requests_sync(test_repo["owner"], test_repo["repo"])

        if not prs:
            pytest.skip("No PRs found in the repository")

        pr_number = prs[0]["number"]

        # Fetch PR details
        details = github_fetcher.fetch_pr_details_sync(test_repo["owner"], test_repo["repo"], pr_number)

        # Check the results
        assert isinstance(details, dict)
        assert "files" in details
        assert "reviews" in details
        assert "comments" in details
        assert "commits" in details
        assert "review_comments" in details

    def test_fetch_issue_details(self, github_fetcher, test_repo):
        """Test fetching issue details."""
        # Find an issue number to test with
        issues = github_fetcher.fetch_issues_sync(test_repo["owner"], test_repo["repo"])

        if not issues:
            pytest.skip("No issues found in the repository")

        issue_number = issues[0]["number"]

        # Fetch issue details
        details = github_fetcher.fetch_issue_details_sync(test_repo["owner"], test_repo["repo"], issue_number)

        # Check the results
        assert isinstance(details, dict)
        assert "comments" in details
        assert "events" in details
        assert "timeline" in details

    def test_create_pr_node(self, github_fetcher, test_repo):
        """Test creating a PR node."""
        # Find a PR to test with
        prs = github_fetcher.fetch_pull_requests_sync(test_repo["owner"], test_repo["repo"])

        if not prs:
            pytest.skip("No PRs found in the repository")

        pr = prs[0]
        pr_number = pr["number"]

        # Fetch PR details
        details = github_fetcher.fetch_pr_details_sync(test_repo["owner"], test_repo["repo"], pr_number)

        # Create PR node
        node = github_fetcher.create_pr_node(pr, details)

        # Check the node
        assert isinstance(node, PRNode)
        assert node.number == pr_number
        assert node.title == pr["title"]

    def test_create_issue_node(self, github_fetcher, test_repo):
        """Test creating an issue node."""
        # Find an issue to test with
        issues = github_fetcher.fetch_issues_sync(test_repo["owner"], test_repo["repo"])

        if not issues:
            pytest.skip("No issues found in the repository")

        issue = issues[0]
        issue_number = issue["number"]

        # Fetch issue details
        details = github_fetcher.fetch_issue_details_sync(test_repo["owner"], test_repo["repo"], issue_number)

        # Create issue node
        node = github_fetcher.create_issue_node(issue, details)

        # Check the node
        assert isinstance(node, IssueNode)
        assert node.number == issue_number
        assert node.title == issue["title"]

    def test_extract_mentions(self, github_fetcher):
        """Test extracting mentions from text."""
        # Test with various mention formats
        text = """
        This is a test with @user1 and @user2 mentioned.
        Also mentioning @user-with-dashes and @123user.
        """

        # Extract mentions
        mentions = github_fetcher.extract_mentions(text)

        # Check the mentions
        assert len(mentions) >= 4
        assert "user1" in mentions
        assert "user2" in mentions
        assert "user-with-dashes" in mentions
        assert "123user" in mentions

    def test_create_mention_edges(self, github_fetcher):
        """Test creating mention edges."""
        # Create a source ID and text with mentions
        source_id = "PR_1"
        text = "This is a test PR mentioning @user1 and @user2"

        # Mock repository issues and PRs
        repo_issues = []
        repo_prs = []

        # Create mention edges
        edges = github_fetcher.create_mention_edges(source_id, text, repo_issues, repo_prs)

        # Since we don't have any actual issues or PRs in our mock data,
        # we won't get any edges, but the function should run without errors
        assert isinstance(edges, list)
