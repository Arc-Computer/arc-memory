"""Unit tests for GitHub REST client."""

import json
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from arc_memory.errors import GitHubAuthError, IngestError
from arc_memory.ingest.github_rest import GitHubRESTClient, DEFAULT_RETRY_COUNT, RATE_LIMIT_BUFFER


# No longer needed as we create mock responses in each test


@pytest.fixture
def rest_client():
    """Create a GitHubRESTClient."""
    with patch("arc_memory.ingest.github_rest.requests.get") as mock_get:
        # Mock the rate limit response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resources": {
                "core": {
                    "limit": 5000,
                    "remaining": 4900,
                    "reset": int(time.time()) + 3600,
                }
            }
        }
        mock_get.return_value = mock_response

        client = GitHubRESTClient("test-token")
        return client


class TestGitHubRESTClient:
    """Tests for GitHubRESTClient."""

    def test_init(self, rest_client):
        """Test initialization."""
        assert rest_client.token == "test-token"
        assert rest_client.headers["Authorization"] == "token test-token"
        assert rest_client.headers["Accept"] == "application/vnd.github.v3+json"
        assert rest_client.rate_limit_remaining == 4900
        assert rest_client.rate_limit_limit == 5000
        assert isinstance(rest_client.rate_limit_reset, datetime)

    def test_request_success(self, rest_client):
        """Test successful request."""
        # Create a mock response with proper headers
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "test-repo"}
        mock_response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1619712000",
            "X-RateLimit-Limit": "5000",
        }

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
                timeout=30,
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
            "X-RateLimit-Limit": "5000",
        }

        # Set retry_count to 0 to avoid any retries
        with patch("requests.request", return_value=mock_response) as mock_request:
            # Make request and check for error
            with pytest.raises(IngestError) as excinfo:
                rest_client.request("GET", "/repos/test-owner/test-repo", retry_count=0)
            assert "rate limit" in str(excinfo.value).lower()
            # With retry_count=0, we should get the "after 0 retries" message
            assert "after 0 retries" in str(excinfo.value).lower()

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
        # Return 100 items to ensure we don't hit the "len(response_data) < per_page" condition
        page1_items = [{"id": i, "name": f"item{i}"} for i in range(1, 101)]
        page1_response.json.return_value = page1_items

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
            page = kwargs.get("params", {}).get("page")
            if page == 1:
                return page1_response
            else:
                return page2_response

        with patch("requests.request", side_effect=mock_request_side_effect) as mock_request:
            # Make paginated request
            results = rest_client.paginate("GET", "/repos/test-owner/test-repo/issues", max_pages=2)

            # Check results
            assert len(results) == 101  # 100 from page 1 + 1 from page 2
            assert results[0]["name"] == "item1"
            assert results[99]["name"] == "item100"  # Last item from page 1
            assert results[100]["name"] == "item3"  # From page 2

            # Check that we made two requests
            assert mock_request.call_count == 2

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

    # Enhanced functionality tests

    def test_update_rate_limit_info(self, rest_client):
        """Test updating rate limit info."""
        with patch("arc_memory.ingest.github_rest.requests.get") as mock_get:
            # Mock the rate limit response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "resources": {
                    "core": {
                        "limit": 5000,
                        "remaining": 4800,
                        "reset": int(time.time()) + 3600,
                    }
                }
            }
            mock_get.return_value = mock_response

            # Update rate limit info
            rest_client._update_rate_limit_info()

            # Check that the rate limit info was updated
            assert rest_client.rate_limit_remaining == 4800
            assert rest_client.rate_limit_limit == 5000
            assert isinstance(rest_client.rate_limit_reset, datetime)

    def test_should_wait_for_rate_limit(self, rest_client):
        """Test checking if we should wait for rate limit to reset."""
        # Set up a low rate limit
        rest_client.rate_limit_remaining = 50
        rest_client.rate_limit_reset = datetime.now() + timedelta(minutes=5)

        # Check if we should wait
        should_wait, wait_seconds = rest_client._should_wait_for_rate_limit()

        # We should wait
        assert should_wait is True
        assert wait_seconds > 0
        assert wait_seconds <= 301  # 5 minutes + 1 second buffer

        # Set up a high rate limit
        rest_client.rate_limit_remaining = 4900

        # Check if we should wait
        should_wait, wait_seconds = rest_client._should_wait_for_rate_limit()

        # We should not wait
        assert should_wait is False
        assert wait_seconds == 0

    def test_request_with_retry(self, rest_client):
        """Test making a request with retry logic."""
        with patch("arc_memory.ingest.github_rest.requests.request") as mock_request:
            # Mock a successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"key": "value"}
            mock_response.headers = {
                "X-RateLimit-Remaining": "4899",
                "X-RateLimit-Reset": str(int(time.time()) + 3600),
                "X-RateLimit-Limit": "5000",
            }
            mock_request.return_value = mock_response

            # Make a request
            result = rest_client.request("GET", "/test")

            # Check the result
            assert result == {"key": "value"}

            # Check that the request was made with the correct parameters
            mock_request.assert_called_once()
            _, kwargs = mock_request.call_args
            assert kwargs["method"] == "GET"
            assert kwargs["url"] == "https://api.github.com/test"
            assert kwargs["headers"] == rest_client.headers
            assert kwargs["timeout"] == 30

    def test_request_with_rate_limit_exceeded(self, rest_client):
        """Test handling rate limit exceeded."""
        with patch("arc_memory.ingest.github_rest.requests.request") as mock_request, \
             patch("arc_memory.ingest.github_rest.time.sleep") as mock_sleep:
            # Mock a rate limit exceeded response followed by a successful response
            mock_rate_limit_response = MagicMock()
            mock_rate_limit_response.status_code = 403
            mock_rate_limit_response.text = "API rate limit exceeded"
            mock_rate_limit_response.headers = {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + 60),
                "X-RateLimit-Limit": "5000",
            }

            mock_success_response = MagicMock()
            mock_success_response.status_code = 200
            mock_success_response.json.return_value = {"key": "value"}
            mock_success_response.headers = {
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": str(int(time.time()) + 3600),
                "X-RateLimit-Limit": "5000",
            }

            # Set up the mock to return the rate limit response first, then the success response
            mock_request.side_effect = [mock_rate_limit_response, mock_success_response]

            # Make a request
            result = rest_client.request("GET", "/test")

            # Check the result
            assert result == {"key": "value"}

            # Check that sleep was called
            mock_sleep.assert_called_once()

            # Check that the request was made twice
            assert mock_request.call_count == 2

    def test_request_with_server_error(self, rest_client):
        """Test handling server errors with retry."""
        with patch("arc_memory.ingest.github_rest.requests.request") as mock_request, \
             patch("arc_memory.ingest.github_rest.time.sleep") as mock_sleep:
            # Mock a server error response followed by a successful response
            mock_server_error_response = MagicMock()
            mock_server_error_response.status_code = 500
            mock_server_error_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")

            mock_success_response = MagicMock()
            mock_success_response.status_code = 200
            mock_success_response.json.return_value = {"key": "value"}
            mock_success_response.headers = {
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": str(int(time.time()) + 3600),
                "X-RateLimit-Limit": "5000",
            }

            # Set up the mock to return the server error response first, then the success response
            mock_request.side_effect = [mock_server_error_response, mock_success_response]

            # Make a request
            result = rest_client.request("GET", "/test")

            # Check the result
            assert result == {"key": "value"}

            # Check that sleep was called
            mock_sleep.assert_called_once()

            # Check that the request was made twice
            assert mock_request.call_count == 2

    def test_request_with_network_error(self, rest_client):
        """Test handling network errors with retry."""
        with patch("arc_memory.ingest.github_rest.requests.request") as mock_request, \
             patch("arc_memory.ingest.github_rest.time.sleep") as mock_sleep:
            # Mock a network error followed by a successful response
            mock_request.side_effect = [
                requests.exceptions.ConnectionError("Connection error"),
                MagicMock(
                    status_code=200,
                    json=lambda: {"key": "value"},
                    headers={
                        "X-RateLimit-Remaining": "4999",
                        "X-RateLimit-Reset": str(int(time.time()) + 3600),
                        "X-RateLimit-Limit": "5000",
                    }
                )
            ]

            # Make a request
            result = rest_client.request("GET", "/test")

            # Check the result
            assert result == {"key": "value"}

            # Check that sleep was called
            mock_sleep.assert_called_once()

            # Check that the request was made twice
            assert mock_request.call_count == 2

    def test_batch_request(self, rest_client):
        """Test batch requests."""
        with patch.object(rest_client, "request") as mock_request, \
             patch("arc_memory.ingest.github_rest.time.sleep") as mock_sleep:
            # Mock responses for each endpoint
            mock_request.side_effect = [
                {"id": 1},
                {"id": 2},
                {"id": 3},
            ]

            # Make a batch request
            result = rest_client.batch_request("GET", ["/test/1", "/test/2", "/test/3"], batch_size=2)

            # Check the result
            assert result == [{"id": 1}, {"id": 2}, {"id": 3}]

            # Check that the request was made three times
            assert mock_request.call_count == 3

            # Check that sleep was called once (between batches)
            assert mock_sleep.call_count == 1

    def test_get_commits_for_pr(self, rest_client):
        """Test getting commits for a PR."""
        with patch.object(rest_client, "paginate") as mock_paginate:
            # Mock the paginate response
            mock_paginate.return_value = [
                {"sha": "abc123", "commit": {"message": "Test commit 1"}},
                {"sha": "def456", "commit": {"message": "Test commit 2"}},
            ]

            # Get commits for PR
            result = rest_client.get_commits_for_pr("owner", "repo", 123)

            # Check the result
            assert result == [
                {"sha": "abc123", "commit": {"message": "Test commit 1"}},
                {"sha": "def456", "commit": {"message": "Test commit 2"}},
            ]

            # Check that paginate was called with the correct parameters
            mock_paginate.assert_called_once_with("GET", "/repos/owner/repo/pulls/123/commits")

    def test_get_review_comments(self, rest_client):
        """Test getting review comments for a PR."""
        with patch.object(rest_client, "paginate") as mock_paginate:
            # Mock the paginate response
            mock_paginate.return_value = [
                {"id": 1, "user": {"login": "reviewer1"}, "body": "Review comment 1"},
                {"id": 2, "user": {"login": "reviewer2"}, "body": "Review comment 2"},
            ]

            # Get review comments
            result = rest_client.get_review_comments("owner", "repo", 123)

            # Check the result
            assert result == [
                {"id": 1, "user": {"login": "reviewer1"}, "body": "Review comment 1"},
                {"id": 2, "user": {"login": "reviewer2"}, "body": "Review comment 2"},
            ]

            # Check that paginate was called with the correct parameters
            mock_paginate.assert_called_once_with("GET", "/repos/owner/repo/pulls/123/comments")

    def test_get_issue_events(self, rest_client):
        """Test getting events for an issue."""
        with patch.object(rest_client, "paginate") as mock_paginate:
            # Mock the paginate response
            mock_paginate.return_value = [
                {"event": "labeled", "label": {"name": "bug"}},
                {"event": "assigned", "assignee": {"login": "test-user"}},
            ]

            # Get issue events
            result = rest_client.get_issue_events("owner", "repo", 123)

            # Check the result
            assert result == [
                {"event": "labeled", "label": {"name": "bug"}},
                {"event": "assigned", "assignee": {"login": "test-user"}},
            ]

            # Check that paginate was called with the correct parameters
            mock_paginate.assert_called_once_with("GET", "/repos/owner/repo/issues/123/events")

    def test_get_issue_timeline(self, rest_client):
        """Test getting issue timeline."""
        with patch.object(rest_client, "paginate") as mock_paginate:
            # Mock the paginate response
            mock_paginate.return_value = [
                {"event": "labeled", "label": {"name": "bug"}},
                {"event": "assigned", "assignee": {"login": "test-user"}},
            ]

            # Get issue timeline
            result = rest_client.get_issue_timeline("owner", "repo", 123)

            # Check the result
            assert result == [
                {"event": "labeled", "label": {"name": "bug"}},
                {"event": "assigned", "assignee": {"login": "test-user"}},
            ]

            # Check that paginate was called with the correct parameters
            mock_paginate.assert_called_once_with("GET", "/repos/owner/repo/issues/123/timeline")

            # Check that the Accept header was set correctly and then restored
            assert rest_client.headers["Accept"] == "application/vnd.github.v3+json"

    def test_get_pr_details_batch(self, rest_client):
        """Test getting PR details in batch."""
        with patch.object(rest_client, "batch_request") as mock_batch_request:
            # Mock the batch_request response
            mock_batch_request.return_value = [
                {"number": 1, "title": "PR 1"},
                {"number": 2, "title": "PR 2"},
                {"number": 3, "title": "PR 3"},
            ]

            # Get PR details in batch
            result = rest_client.get_pr_details_batch("owner", "repo", [1, 2, 3])

            # Check the result
            assert result == [
                {"number": 1, "title": "PR 1"},
                {"number": 2, "title": "PR 2"},
                {"number": 3, "title": "PR 3"},
            ]

            # Check that batch_request was called with the correct parameters
            mock_batch_request.assert_called_once_with(
                "GET",
                ["/repos/owner/repo/pulls/1", "/repos/owner/repo/pulls/2", "/repos/owner/repo/pulls/3"]
            )

    def test_get_issue_details_batch(self, rest_client):
        """Test getting issue details in batch."""
        with patch.object(rest_client, "batch_request") as mock_batch_request:
            # Mock the batch_request response
            mock_batch_request.return_value = [
                {"number": 1, "title": "Issue 1"},
                {"number": 2, "title": "Issue 2"},
                {"number": 3, "title": "Issue 3"},
            ]

            # Get issue details in batch
            result = rest_client.get_issue_details_batch("owner", "repo", [1, 2, 3])

            # Check the result
            assert result == [
                {"number": 1, "title": "Issue 1"},
                {"number": 2, "title": "Issue 2"},
                {"number": 3, "title": "Issue 3"},
            ]

            # Check that batch_request was called with the correct parameters
            mock_batch_request.assert_called_once_with(
                "GET",
                ["/repos/owner/repo/issues/1", "/repos/owner/repo/issues/2", "/repos/owner/repo/issues/3"]
            )
