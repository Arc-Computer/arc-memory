"""GitHub GraphQL API client for Arc Memory.

This module provides a client for interacting with GitHub's GraphQL API,
following GitHub's latest standards and best practices.
"""

import asyncio
import logging
import time
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
USER_AGENT = "Arc-Memory/0.5.0"  # TODO: Use version from a central version file
REQUEST_TIMEOUT = 9  # GitHub has a 10-second timeout, so we use 9 seconds
MAX_RETRIES = 5  # Maximum number of retries for rate-limited requests
MAX_CONCURRENT_REQUESTS = 10  # GitHub allows up to 100, but we use a lower limit to be safe


class GitHubGraphQLClient:
    """GraphQL client for GitHub API.

    This client follows GitHub's latest standards and best practices:
    - Uses Bearer token authentication
    - Handles rate limits with proper backoff
    - Implements pagination correctly
    - Handles errors appropriately
    - Limits concurrent requests
    - Sets appropriate timeouts
    """

    def __init__(self, token: str):
        """Initialize the GraphQL client.

        Args:
            token: GitHub token to use for API calls.
        """
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github.v4+json",  # Explicitly request GraphQL API v4
        }

        # Semaphore to limit concurrent requests
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        # Only initialize the client if gql is available
        if GQL_AVAILABLE:
            self.transport = AIOHTTPTransport(
                url=GITHUB_GRAPHQL_URL,
                headers=self.headers,
                ssl=True,  # Explicitly verify SSL certificates
                timeout=REQUEST_TIMEOUT,  # Set timeout to avoid GitHub's 10-second limit
            )
            self.client = Client(
                transport=self.transport,
                fetch_schema_from_transport=True,
            )
        else:
            logger.warning("gql library not available, GraphQL client will not work")
            self.transport = None
            self.client = None

        # Rate limit tracking
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    async def execute_query(self, query_str: str, variables: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """Execute a GraphQL query with retry logic for rate limits.

        Args:
            query_str: The GraphQL query string.
            variables: Variables for the query.
            retry_count: Current retry attempt (used internally for recursion).

        Returns:
            The query result.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error executing the query after all retries.
        """
        # Check if gql is available
        if not GQL_AVAILABLE:
            logger.error("gql library not available, cannot execute GraphQL query")
            raise IngestError("gql library not available, cannot execute GraphQL query")

        # Use semaphore to limit concurrent requests
        async with self.semaphore:
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
                error_message = str(e)

                # Check for authentication errors
                if "401" in error_message or "Unauthorized" in error_message:
                    logger.error(f"GitHub authentication error: {e}")
                    raise GitHubAuthError(f"GitHub authentication error: {e}")

                # Check for primary rate limit errors
                if "403" in error_message and "rate limit" in error_message.lower():
                    logger.warning(f"GitHub primary rate limit exceeded: {e}")

                    # If we've already retried too many times, raise the error
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Maximum retries ({MAX_RETRIES}) exceeded for rate limit")
                        raise IngestError(f"GitHub rate limit exceeded after {MAX_RETRIES} retries: {e}")

                    # Calculate wait time based on rate limit reset or use exponential backoff
                    wait_time = 0
                    if self.rate_limit_reset:
                        now = datetime.now()
                        if now < self.rate_limit_reset:
                            wait_time = (self.rate_limit_reset - now).total_seconds() + 10

                    # If we couldn't determine wait time from headers, use exponential backoff
                    if wait_time <= 0:
                        wait_time = min(2 ** retry_count, 60)  # Cap at 60 seconds

                    logger.info(f"Waiting {wait_time:.1f} seconds before retry {retry_count + 1}/{MAX_RETRIES}")
                    await asyncio.sleep(wait_time)

                    # Retry the query with incremented retry count
                    return await self.execute_query(query_str, variables, retry_count + 1)

                # Check for secondary rate limit errors
                if "403" in error_message and ("secondary rate limit" in error_message.lower() or
                                              "abuse detection" in error_message.lower()):
                    logger.warning(f"GitHub secondary rate limit exceeded: {e}")

                    # If we've already retried too many times, raise the error
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Maximum retries ({MAX_RETRIES}) exceeded for secondary rate limit")
                        raise IngestError(f"GitHub secondary rate limit exceeded after {MAX_RETRIES} retries: {e}")

                    # Use Retry-After header if available, or exponential backoff
                    # GitHub typically suggests 60 seconds for secondary rate limits
                    wait_time = min(60 * (retry_count + 1), 300)  # Increase wait time with each retry, cap at 5 minutes

                    logger.info(f"Secondary rate limit hit. Waiting {wait_time:.1f} seconds before retry {retry_count + 1}/{MAX_RETRIES}")
                    await asyncio.sleep(wait_time)

                    # Retry the query with incremented retry count
                    return await self.execute_query(query_str, variables, retry_count + 1)

                # Other query errors
                logger.error(f"GraphQL query error: {e}")
                raise IngestError(f"GraphQL query error: {e}")
            except asyncio.TimeoutError:
                logger.warning(f"GitHub API request timed out after {REQUEST_TIMEOUT} seconds")

                # If we've already retried too many times, raise the error
                if retry_count >= MAX_RETRIES:
                    logger.error(f"Maximum retries ({MAX_RETRIES}) exceeded for timeout")
                    raise IngestError(f"GitHub API request timed out after {MAX_RETRIES} retries")

                # Use exponential backoff for timeouts
                wait_time = min(2 ** retry_count, 30)  # Cap at 30 seconds
                logger.info(f"Waiting {wait_time:.1f} seconds before retry {retry_count + 1}/{MAX_RETRIES}")
                await asyncio.sleep(wait_time)

                # Retry the query with incremented retry count
                return await self.execute_query(query_str, variables, retry_count + 1)
            except Exception as e:
                error_message = str(e)

                # Check for authentication errors in the exception message
                if "401" in error_message or "Unauthorized" in error_message:
                    logger.error(f"GitHub authentication error: {e}")
                    raise GitHubAuthError(f"GitHub authentication error: {e}")

                # Check for other specific error types in the exception message
                if "500" in error_message or "Internal Server Error" in error_message:
                    logger.error(f"GitHub server error: {e}")

                    # If we've already retried too many times, raise the error
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Maximum retries ({MAX_RETRIES}) exceeded for server error")
                        raise IngestError(f"GitHub server error after {MAX_RETRIES} retries: {e}")

                    # Use exponential backoff for server errors
                    wait_time = min(2 ** retry_count, 60)  # Cap at 60 seconds
                    logger.info(f"Waiting {wait_time:.1f} seconds before retry {retry_count + 1}/{MAX_RETRIES}")
                    await asyncio.sleep(wait_time)

                    # Retry the query with incremented retry count
                    return await self.execute_query(query_str, variables, retry_count + 1)

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
        page_count = 0
        total_items = 0

        while has_next_page:
            page_count += 1

            # Update cursor in variables
            if cursor:
                variables["cursor"] = cursor

            # Execute the query with retry logic
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
                nodes_count = len(nodes)
                all_items.extend(nodes)
            else:
                nodes_count = 1  # Just counting pages
                all_items.append(paginated_field)

            total_items += nodes_count

            # Log progress
            logger.debug(f"Fetched page {page_count} with {nodes_count} items, total: {total_items}, has next page: {has_next_page}")

            # Add a small delay between pages to avoid hitting secondary rate limits
            # This is a best practice recommended by GitHub
            if has_next_page:
                await asyncio.sleep(0.5)  # 500ms delay between pages

        logger.info(f"Completed pagination with {page_count} pages and {total_items} total items")
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
        # Create a new event loop for thread safety
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
        # Create a new event loop for thread safety
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
