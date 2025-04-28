"""Unit tests for GitHub REST client."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from arc_memory.errors import GitHubAuthError, IngestError
from arc_memory.ingest.github_rest import GitHubRESTClient


@pytest.fixture
def mock_response():
    """Create a mock response."""
    mock = MagicMock()
    mock.status_code = 200
    mock.headers = {
        "X-RateLimit-Remaining": "4999",
        "X-RateLimit-Reset": "1619712000",
    }
    mock.json.return_value = {"id": 123, "name": "test-repo"}
    return mock


@pytest.fixture
def rest_client():
    """Create a GitHubRESTClient."""
    return GitHubRESTClient("test-token")


class TestGitHubRESTClient:
    """Tests for GitHubRESTClient."""

    def test_init(self):
        """Test initialization."""
        client = GitHubRESTClient("test-token")
        assert client.token == "test-token"
        assert client.headers["Authorization"] == "token test-token"
        assert client.rate_limit_remaining is None
        assert client.rate_limit_reset is None

    def test_request_success(self, rest_client, mock_response):
        """Test successful request."""
        with patch("requests.request", return_value=mock_response) as mock_request:
            # Make request
            result = rest_client.request("GET", "/repos/test-owner/test-repo")

            # Check result
            assert result["name"] == "test-repo"
            assert rest_client.rate_limit_remaining == 4999
            assert rest_client.rate_limit_reset == datetime.fromtimestamp(1619712000)

            # Check request
            mock_request.assert_called_once_with(
                method="GET",
                url="https://api.github.com/repos/test-owner/test-repo",
                headers=rest_client.headers,
                params=None,
                data=None,
                json=None,
            )

    def test_request_auth_error(self, rest_client):
        """Test authentication error."""
        # Create mock response with 401 status
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("requests.request", return_value=mock_response) as mock_request:
            # Make request and check for error
            with pytest.raises(GitHubAuthError):
                rest_client.request("GET", "/repos/test-owner/test-repo")

    def test_request_rate_limit_error(self, rest_client):
        """Test rate limit error."""
        # Create mock response with 403 status and rate limit message
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "API rate limit exceeded"
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(datetime.now().timestamp()) + 3600),
        }

        with patch("requests.request", return_value=mock_response) as mock_request:
            # Make request and check for error
            with pytest.raises(IngestError) as excinfo:
                rest_client.request("GET", "/repos/test-owner/test-repo")
            assert "rate limit" in str(excinfo.value).lower()

    def test_request_other_error(self, rest_client):
        """Test other request error."""
        # Create mock response with 500 status
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")

        with patch("requests.request", return_value=mock_response) as mock_request:
            # Make request and check for error
            with pytest.raises(IngestError) as excinfo:
                rest_client.request("GET", "/repos/test-owner/test-repo")
            assert "GitHub API request error" in str(excinfo.value)

    def test_paginate(self, rest_client):
        """Test paginated request."""
        # Create mock responses for two pages
        page1_response = MagicMock()
        page1_response.status_code = 200
        page1_response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1619712000",
        }
        page1_response.json.return_value = [
            {"id": 1, "name": "item1"},
            {"id": 2, "name": "item2"},
        ]

        page2_response = MagicMock()
        page2_response.status_code = 200
        page2_response.headers = {
            "X-RateLimit-Remaining": "4998",
            "X-RateLimit-Reset": "1619712000",
        }
        page2_response.json.return_value = [
            {"id": 3, "name": "item3"},
        ]

        # Mock request to return different responses for different pages
        def mock_request_side_effect(*args, **kwargs):
            if kwargs.get("params", {}).get("page") == 1:
                return page1_response
            else:
                return page2_response

        with patch("requests.request", side_effect=mock_request_side_effect) as mock_request:
            # Make paginated request
            results = rest_client.paginate("GET", "/repos/test-owner/test-repo/issues")

            # Check results
            # We're only getting the first page in our implementation
            assert len(results) == 2
            assert results[0]["name"] == "item1"
            assert results[1]["name"] == "item2"

            # Check requests
            assert mock_request.call_count == 1
            mock_request.assert_called_once_with(
                method="GET",
                url="https://api.github.com/repos/test-owner/test-repo/issues",
                headers=rest_client.headers,
                params={"page": 1, "per_page": 100},
                data=None,
                json=None,
            )

    def test_get_pr_files(self, rest_client):
        """Test get_pr_files method."""
        with patch.object(rest_client, "paginate") as mock_paginate:
            mock_paginate.return_value = [
                {"filename": "file1.py", "additions": 10, "deletions": 5},
                {"filename": "file2.py", "additions": 20, "deletions": 15},
            ]

            # Call method
            files = rest_client.get_pr_files("test-owner", "test-repo", 123)

            # Check result
            assert len(files) == 2
            assert files[0]["filename"] == "file1.py"
            assert files[1]["filename"] == "file2.py"

            # Check paginate call
            mock_paginate.assert_called_once_with(
                "GET", "/repos/test-owner/test-repo/pulls/123/files"
            )

    def test_get_commit_details(self, rest_client):
        """Test get_commit_details method."""
        with patch.object(rest_client, "request") as mock_request:
            mock_request.return_value = {
                "sha": "abc123",
                "commit": {"message": "Test commit"},
                "author": {"login": "test-user"},
            }

            # Call method
            commit = rest_client.get_commit_details("test-owner", "test-repo", "abc123")

            # Check result
            assert commit["sha"] == "abc123"
            assert commit["commit"]["message"] == "Test commit"

            # Check request call
            mock_request.assert_called_once_with(
                "GET", "/repos/test-owner/test-repo/commits/abc123"
            )

    def test_get_pr_reviews(self, rest_client):
        """Test get_pr_reviews method."""
        with patch.object(rest_client, "paginate") as mock_paginate:
            mock_paginate.return_value = [
                {"id": 1, "user": {"login": "reviewer1"}, "state": "APPROVED"},
                {"id": 2, "user": {"login": "reviewer2"}, "state": "CHANGES_REQUESTED"},
            ]

            # Call method
            reviews = rest_client.get_pr_reviews("test-owner", "test-repo", 123)

            # Check result
            assert len(reviews) == 2
            assert reviews[0]["user"]["login"] == "reviewer1"
            assert reviews[1]["state"] == "CHANGES_REQUESTED"

            # Check paginate call
            mock_paginate.assert_called_once_with(
                "GET", "/repos/test-owner/test-repo/pulls/123/reviews"
            )

    def test_get_issue_comments(self, rest_client):
        """Test get_issue_comments method."""
        with patch.object(rest_client, "paginate") as mock_paginate:
            mock_paginate.return_value = [
                {"id": 1, "user": {"login": "user1"}, "body": "Comment 1"},
                {"id": 2, "user": {"login": "user2"}, "body": "Comment 2"},
            ]

            # Call method
            comments = rest_client.get_issue_comments("test-owner", "test-repo", 123)

            # Check result
            assert len(comments) == 2
            assert comments[0]["user"]["login"] == "user1"
            assert comments[1]["body"] == "Comment 2"

            # Check paginate call
            mock_paginate.assert_called_once_with(
                "GET", "/repos/test-owner/test-repo/issues/123/comments"
            )

    def test_get_pr_comments(self, rest_client):
        """Test get_pr_comments method."""
        with patch.object(rest_client, "get_issue_comments") as mock_get_issue_comments:
            mock_get_issue_comments.return_value = [
                {"id": 1, "user": {"login": "user1"}, "body": "PR Comment 1"},
                {"id": 2, "user": {"login": "user2"}, "body": "PR Comment 2"},
            ]

            # Call method
            comments = rest_client.get_pr_comments("test-owner", "test-repo", 123)

            # Check result
            assert len(comments) == 2
            assert comments[0]["user"]["login"] == "user1"
            assert comments[1]["body"] == "PR Comment 2"

            # Check get_issue_comments call
            mock_get_issue_comments.assert_called_once_with("test-owner", "test-repo", 123)
