"""GitHub GraphQL API client for Arc Memory."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import aiohttp
    from gql import Client, gql
    from gql.transport.aiohttp import AIOHTTPTransport
    from gql.transport.exceptions import TransportQueryError
    GQL_AVAILABLE = True
except ImportError:
    # For testing without gql installed
    GQL_AVAILABLE = False
    # Define placeholder classes for testing
    class Client:
        def __init__(self, *args, **kwargs):
            pass
    class AIOHTTPTransport:
        def __init__(self, *args, **kwargs):
            pass
    class TransportQueryError(Exception):
        pass
    def gql(query_string):
        return query_string

from arc_memory.errors import GitHubAuthError, IngestError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Constants
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
USER_AGENT = "Arc-Memory/0.2.2"


class GitHubGraphQLClient:
    """GraphQL client for GitHub API."""

    def __init__(self, token: str):
        """Initialize the GraphQL client.

        Args:
            token: GitHub token to use for API calls.
        """
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        }

        # Only initialize the client if gql is available
        if GQL_AVAILABLE:
            self.transport = AIOHTTPTransport(
                url=GITHUB_GRAPHQL_URL,
                headers=self.headers,
                ssl=True,  # Explicitly verify SSL certificates
            )
            self.client = Client(
                transport=self.transport,
                fetch_schema_from_transport=True,
            )
        else:
            logger.warning("gql library not available, GraphQL client will not work")
            self.transport = None
            self.client = None

        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    async def execute_query(self, query_str: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GraphQL query.

        Args:
            query_str: The GraphQL query string.
            variables: Variables for the query.

        Returns:
            The query result.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error executing the query.
        """
        # Check if gql is available
        if not GQL_AVAILABLE:
            logger.error("gql library not available, cannot execute GraphQL query")
            raise IngestError("gql library not available, cannot execute GraphQL query")

        try:
            # Parse the query
            query = gql(query_str)

            # Execute the query
            result = await self.client.execute_async(query, variable_values=variables)

            # Check for rate limit info in the result
            if "rateLimit" in result:
                self.rate_limit_remaining = result["rateLimit"]["remaining"]
                # Handle resetAt which could be a string or a timestamp
                reset_at = result["rateLimit"]["resetAt"]
                if isinstance(reset_at, str):
                    # Parse ISO format string
                    self.rate_limit_reset = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
                else:
                    # Handle as timestamp
                    self.rate_limit_reset = datetime.fromtimestamp(reset_at)
                logger.debug(f"Rate limit: {self.rate_limit_remaining} remaining, resets at {self.rate_limit_reset}")

            return result
        except TransportQueryError as e:
            # Check for authentication errors
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error(f"GitHub authentication error: {e}")
                raise GitHubAuthError(f"GitHub authentication error: {e}")

            # Check for rate limit errors
            if "403" in str(e) and "rate limit" in str(e).lower():
                logger.error(f"GitHub rate limit exceeded: {e}")
                raise IngestError(f"GitHub rate limit exceeded: {e}")

            # Other query errors
            logger.error(f"GraphQL query error: {e}")
            raise IngestError(f"GraphQL query error: {e}")
        except Exception as e:
            # Check for authentication errors in the exception message
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error(f"GitHub authentication error: {e}")
                raise GitHubAuthError(f"GitHub authentication error: {e}")

            # Check for other specific error types in the exception message
            if "500" in str(e) or "Internal Server Error" in str(e):
                logger.error(f"GraphQL query error: {e}")
                raise IngestError(f"GraphQL query error: {e}")

            logger.exception(f"Unexpected error executing GraphQL query: {e}")
            raise IngestError(f"Failed to execute GraphQL query: {e}")

    async def paginate_query(
        self,
        query_str: str,
        variables: Dict[str, Any],
        path: List[str],
        extract_nodes: bool = True,
    ) -> List[Dict[str, Any]]:
        """Execute a paginated GraphQL query.

        Args:
            query_str: The GraphQL query string.
            variables: Variables for the query.
            path: Path to the paginated field in the result.
            extract_nodes: Whether to extract nodes from the result.

        Returns:
            A list of result items.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error executing the query.
        """
        all_items = []
        has_next_page = True
        cursor = None

        while has_next_page:
            # Update cursor in variables
            if cursor:
                variables["cursor"] = cursor

            # Execute the query
            result = await self.execute_query(query_str, variables)

            # Navigate to the paginated field
            current = result
            for key in path[:-1]:
                current = current.get(key, {})

            # Get the paginated field
            paginated_field = current.get(path[-1], {})

            # Check for page info
            page_info = paginated_field.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

            # Extract nodes if requested
            if extract_nodes:
                nodes = paginated_field.get("nodes", [])
                all_items.extend(nodes)
            else:
                all_items.append(paginated_field)

            # Log progress
            logger.debug(f"Fetched {len(paginated_field.get('nodes', []))} items, has next page: {has_next_page}")

            # Check rate limit and wait if necessary
            if self.rate_limit_remaining is not None and self.rate_limit_remaining < 100:
                now = datetime.now()
                if self.rate_limit_reset and now < self.rate_limit_reset:
                    wait_time = (self.rate_limit_reset - now).total_seconds() + 10
                    logger.warning(f"Rate limit low ({self.rate_limit_remaining}), waiting {wait_time} seconds")
                    await asyncio.sleep(wait_time)

        return all_items

    def execute_query_sync(self, query_str: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GraphQL query synchronously.

        Args:
            query_str: The GraphQL query string.
            variables: Variables for the query.

        Returns:
            The query result.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error executing the query.
        """
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.execute_query(query_str, variables))
        finally:
            loop.close()

    def paginate_query_sync(
        self,
        query_str: str,
        variables: Dict[str, Any],
        path: List[str],
        extract_nodes: bool = True,
    ) -> List[Dict[str, Any]]:
        """Execute a paginated GraphQL query synchronously.

        Args:
            query_str: The GraphQL query string.
            variables: Variables for the query.
            path: Path to the paginated field in the result.
            extract_nodes: Whether to extract nodes from the result.

        Returns:
            A list of result items.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error executing the query.
        """
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.paginate_query(query_str, variables, path, extract_nodes))
        finally:
            loop.close()


# GraphQL query for repository information
REPO_INFO_QUERY = """
query RepoInfo($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    id
    name
    owner {
      login
    }
    createdAt
    updatedAt
    description
    url
  }
  rateLimit {
    limit
    remaining
    resetAt
  }
}
"""

# GraphQL query for pull requests
PULL_REQUESTS_QUERY = """
query PullRequests($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(first: 100, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        body
        state
        createdAt
        updatedAt
        closedAt
        mergedAt
        author {
          login
        }
        baseRefName
        headRefName
        url
        mergeCommit {
          oid
        }
        commits(first: 1) {
          nodes {
            commit {
              oid
            }
          }
        }
        reviews(first: 10) {
          nodes {
            author {
              login
            }
            state
            body
            createdAt
          }
        }
      }
    }
  }
  rateLimit {
    limit
    remaining
    resetAt
  }
}
"""

# GraphQL query for issues
ISSUES_QUERY = """
query Issues($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    issues(first: 100, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        body
        state
        createdAt
        updatedAt
        closedAt
        author {
          login
        }
        url
        labels(first: 10) {
          nodes {
            name
          }
        }
      }
    }
  }
  rateLimit {
    limit
    remaining
    resetAt
  }
}
"""

# GraphQL query for updated pull requests (for incremental builds)
UPDATED_PRS_QUERY = """
query UpdatedPRs($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(first: 100, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        body
        state
        createdAt
        updatedAt
        closedAt
        mergedAt
        author {
          login
        }
        baseRefName
        headRefName
        url
        mergeCommit {
          oid
        }
        commits(first: 1) {
          nodes {
            commit {
              oid
            }
          }
        }
      }
    }
  }
  rateLimit {
    limit
    remaining
    resetAt
  }
}
"""

# GraphQL query for updated issues (for incremental builds)
UPDATED_ISSUES_QUERY = """
query UpdatedIssues($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    issues(first: 100, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        body
        state
        createdAt
        updatedAt
        closedAt
        author {
          login
        }
        url
        labels(first: 10) {
          nodes {
            name
          }
        }
      }
    }
  }
  rateLimit {
    limit
    remaining
    resetAt
  }
}
"""
