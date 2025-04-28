"""Unit tests for GitHub GraphQL client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Mock the TransportQueryError class
class MockTransportQueryError(Exception):
    """Mock for gql.transport.exceptions.TransportQueryError."""
    pass

# Patch the import
with patch("arc_memory.ingest.github_graphql.TransportQueryError", MockTransportQueryError):
    from arc_memory.errors import GitHubAuthError, IngestError
    from arc_memory.ingest.github_graphql import GitHubGraphQLClient, REPO_INFO_QUERY


@pytest.fixture
def mock_client():
    """Create a mock GraphQL client."""
    with patch("arc_memory.ingest.github_graphql.Client") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.execute_async = AsyncMock()
        yield mock_instance


@pytest.fixture
def graphql_client(mock_client):
    """Create a GitHubGraphQLClient with a mock Client."""
    return GitHubGraphQLClient("test-token")


class TestGitHubGraphQLClient:
    """Tests for GitHubGraphQLClient."""

    def test_init(self):
        """Test initialization."""
        client = GitHubGraphQLClient("test-token")
        assert client.token == "test-token"
        assert client.headers["Authorization"] == "Bearer test-token"
        assert client.rate_limit_remaining is None
        assert client.rate_limit_reset is None

    @pytest.mark.asyncio
    async def test_execute_query_success(self, graphql_client, mock_client):
        """Test successful query execution."""
        # Set up mock response
        mock_client.execute_async.return_value = {
            "repository": {
                "id": "R_123",
                "name": "test-repo",
            },
            "rateLimit": {
                "limit": 5000,
                "remaining": 4999,
                "resetAt": 1619712000,
            },
        }

        # Execute query
        result = await graphql_client.execute_query(
            REPO_INFO_QUERY, {"owner": "test-owner", "repo": "test-repo"}
        )

        # Check result
        assert result["repository"]["name"] == "test-repo"
        assert graphql_client.rate_limit_remaining == 4999

    @pytest.mark.asyncio
    async def test_execute_query_auth_error(self, graphql_client, mock_client):
        """Test authentication error."""
        # Set up mock error
        error = MockTransportQueryError("401 Unauthorized")
        mock_client.execute_async.side_effect = error

        # Execute query and check for error
        with pytest.raises(GitHubAuthError):
            await graphql_client.execute_query(
                REPO_INFO_QUERY, {"owner": "test-owner", "repo": "test-repo"}
            )

    @pytest.mark.asyncio
    async def test_execute_query_rate_limit_error(self, graphql_client, mock_client):
        """Test rate limit error."""
        # Set up mock error
        error = MockTransportQueryError("403 Rate limit exceeded")
        mock_client.execute_async.side_effect = error

        # Execute query and check for error
        with pytest.raises(IngestError) as excinfo:
            await graphql_client.execute_query(
                REPO_INFO_QUERY, {"owner": "test-owner", "repo": "test-repo"}
            )
        assert "rate limit" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_execute_query_other_error(self, graphql_client, mock_client):
        """Test other query error."""
        # Set up mock error
        error = MockTransportQueryError("500 Internal Server Error")
        mock_client.execute_async.side_effect = error

        # Execute query and check for error
        with pytest.raises(IngestError) as excinfo:
            await graphql_client.execute_query(
                REPO_INFO_QUERY, {"owner": "test-owner", "repo": "test-repo"}
            )
        assert "GraphQL query error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_paginate_query(self, graphql_client):
        """Test paginated query execution."""
        # Mock execute_query to return paginated results
        async def mock_execute_query(query_str, variables):
            if variables.get("cursor") is None:
                # First page
                return {
                    "repository": {
                        "pullRequests": {
                            "pageInfo": {
                                "hasNextPage": True,
                                "endCursor": "cursor1",
                            },
                            "nodes": [
                                {"id": "PR_1", "number": 1},
                                {"id": "PR_2", "number": 2},
                            ],
                        }
                    }
                }
            else:
                # Second page (last)
                return {
                    "repository": {
                        "pullRequests": {
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                            "nodes": [
                                {"id": "PR_3", "number": 3},
                            ],
                        }
                    }
                }

        graphql_client.execute_query = mock_execute_query

        # Execute paginated query
        results = await graphql_client.paginate_query(
            "query { ... }",
            {"owner": "test-owner", "repo": "test-repo"},
            ["repository", "pullRequests"]
        )

        # Check results
        assert len(results) == 3
        assert results[0]["id"] == "PR_1"
        assert results[1]["id"] == "PR_2"
        assert results[2]["id"] == "PR_3"

    def test_execute_query_sync(self, graphql_client):
        """Test synchronous query execution."""
        # Mock the async method
        async def mock_execute_query(query_str, variables):
            return {"repository": {"name": "test-repo"}}

        graphql_client.execute_query = mock_execute_query

        # Execute synchronous query
        result = graphql_client.execute_query_sync(
            REPO_INFO_QUERY, {"owner": "test-owner", "repo": "test-repo"}
        )

        # Check result
        assert result["repository"]["name"] == "test-repo"

    def test_paginate_query_sync(self, graphql_client):
        """Test synchronous paginated query execution."""
        # Mock the async method
        async def mock_paginate_query(query_str, variables, path, extract_nodes):
            return [
                {"id": "PR_1", "number": 1},
                {"id": "PR_2", "number": 2},
            ]

        graphql_client.paginate_query = mock_paginate_query

        # Execute synchronous paginated query
        results = graphql_client.paginate_query_sync(
            "query { ... }",
            {"owner": "test-owner", "repo": "test-repo"},
            ["repository", "pullRequests"]
        )

        # Check results
        assert len(results) == 2
        assert results[0]["id"] == "PR_1"
        assert results[1]["id"] == "PR_2"
