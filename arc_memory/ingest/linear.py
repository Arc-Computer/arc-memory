"""Linear ingestion for Arc Memory."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from arc_memory.auth.linear import get_linear_token
from arc_memory.errors import IngestError, LinearAuthError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, IssueNode, Node, NodeType

# Import these at runtime to avoid circular imports
# from arc_memory.auth.linear import get_oauth_token_from_keyring, LinearOAuthToken

logger = get_logger(__name__)

# Constants
LINEAR_API_URL = "https://api.linear.app/graphql"
USER_AGENT = "Arc-Memory/0.4.1"

# GraphQL queries
ISSUES_QUERY = """
query Issues($cursor: String) {
  issues(first: 50, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      identifier
      title
      description
      state {
        id
        name
        type
      }
      createdAt
      updatedAt
      archivedAt
      url
      labels {
        nodes {
          id
          name
          color
        }
      }
      assignee {
        id
        name
        email
      }
      creator {
        id
        name
        email
      }
      team {
        id
        name
        key
      }
    }
  }
}
"""

# Alternative query to test basic connectivity
VIEWER_QUERY = """
query {
  viewer {
    id
    name
    email
  }
}
"""


class LinearGraphQLClient:
    """GraphQL client for Linear API."""

    def __init__(self, token: str, is_oauth_token: bool = False):
        """Initialize the GraphQL client.

        Args:
            token: Linear token to use for API calls.
            is_oauth_token: Whether the token is an OAuth token (requires "Bearer" prefix).
        """
        self.token = token
        self.is_oauth_token = is_oauth_token
        self._setup_headers()

    def _setup_headers(self):
        """Set up the headers for API requests based on token type."""
        # Set up headers based on token type
        if self.is_oauth_token:
            # OAuth tokens require the "Bearer" prefix
            auth_header = f"Bearer {self.token}"
        else:
            # API keys are used directly without a prefix
            auth_header = self.token

        self.headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

    def update_token(self, new_token: str):
        """Update the token used for API requests.

        Args:
            new_token: The new token to use.
        """
        self.token = new_token
        self._setup_headers()
        logger.info("Updated Linear API token")

    def execute_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query.

        Args:
            query: The GraphQL query string.
            variables: Variables for the query.

        Returns:
            The query result.

        Raises:
            LinearAuthError: If there's an error with Linear authentication.
            IngestError: If there's an error executing the query.
        """
        # Ensure variables is a dictionary
        variables = variables or {}

        try:
            logger.info(f"Executing Linear GraphQL query with variables: {variables}")
            response = requests.post(
                LINEAR_API_URL,
                headers=self.headers,
                json={"query": query, "variables": variables},
            )
            logger.info(f"Linear API response status code: {response.status_code}")

            # Handle specific HTTP status codes
            if response.status_code == 401:
                token_type = "OAuth token" if self.is_oauth_token else "API key"
                logger.error(f"Linear authentication failed: Unauthorized (401). Invalid {token_type}.")

                # If using OAuth, try to refresh the token
                if self.is_oauth_token:
                    try:
                        from arc_memory.auth.linear import get_oauth_token_from_keyring
                        oauth_token = get_oauth_token_from_keyring()

                        if oauth_token and oauth_token.is_expired():
                            logger.warning("OAuth token is expired. Attempting to refresh...")
                            # Linear tokens have a very long expiration time, so this is unlikely to happen
                            # In a real-world scenario, we would implement token refresh here
                            # TODO: Implement token refresh functionality when Linear supports refresh tokens
                            #       or when we need to handle expired tokens more gracefully.
                            # For now, we'll just raise an error
                            raise LinearAuthError("Linear OAuth token is expired. Please re-authenticate with 'arc auth linear'.")
                    except ImportError:
                        # If we can't import the OAuth functions, just continue with the regular error
                        pass

                raise LinearAuthError(f"Linear authentication failed: Unauthorized. Invalid {token_type}.")

            if response.status_code == 403:
                token_type = "OAuth token" if self.is_oauth_token else "API key"
                logger.error(f"Linear authentication failed: Forbidden (403). {token_type} lacks required permissions.")

                # If using OAuth, provide more specific error message about scopes
                if self.is_oauth_token:
                    raise LinearAuthError(
                        f"Linear authentication failed: Forbidden. Your OAuth token lacks required permissions. "
                        f"Please re-authenticate with 'arc auth linear' to grant the necessary scopes."
                    )

                raise LinearAuthError(f"Linear authentication failed: Forbidden. {token_type} lacks required permissions.")

            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                error_message = data["errors"][0]["message"]
                logger.error(f"Linear GraphQL error: {error_message}")

                # Handle specific GraphQL errors
                if "authentication" in error_message.lower() or "unauthorized" in error_message.lower():
                    token_type = "OAuth token" if self.is_oauth_token else "API key"
                    raise LinearAuthError(f"Linear authentication failed: {error_message}. Please check your {token_type}.")

                if "permission" in error_message.lower() or "access" in error_message.lower():
                    token_type = "OAuth token" if self.is_oauth_token else "API key"
                    scopes = "scopes" if self.is_oauth_token else "permissions"
                    raise LinearAuthError(f"Linear permission error: {error_message}. Your {token_type} may not have the required {scopes}.")

                if "rate limit" in error_message.lower():
                    raise IngestError(f"Linear rate limit exceeded: {error_message}. Please try again later.")

                raise IngestError(f"Linear GraphQL error: {error_message}")

            return data["data"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Linear API request failed: {e}")

            # Handle connection errors
            if isinstance(e, requests.exceptions.ConnectionError):
                raise IngestError(f"Failed to connect to Linear API: {e}. Please check your internet connection.")

            # Handle timeout errors
            if isinstance(e, requests.exceptions.Timeout):
                raise IngestError(f"Linear API request timed out: {e}. Please try again later.")

            # Handle other request errors
            raise IngestError(f"Linear API request failed: {e}")


class LinearIngestor:
    """Ingestor plugin for Linear issues."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "linear"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return [NodeType.ISSUE]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MENTIONS]

    def ingest(
        self,
        repo_path: Path,
        token: Optional[str] = None,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest Linear issues.

        Args:
            repo_path: Path to the repository.
            token: Linear token to use for API calls.
            last_processed: Metadata from the last build for incremental processing.

        Returns:
            A tuple of (nodes, edges, metadata).

        Raises:
            IngestError: If there's an error during ingestion.
        """
        logger.info("Ingesting Linear issues")
        if last_processed:
            logger.info("Performing incremental build")

        try:
            # Get Linear token
            linear_token = get_linear_token(token, allow_failure=True)
            logger.info(f"Linear token found: {linear_token is not None}")
            if not linear_token:
                logger.warning("No Linear token found. Skipping Linear ingestion.")
                return [], [], {"issue_count": 0, "timestamp": datetime.now().isoformat()}

            # Determine if this is an OAuth token
            is_oauth_token = False

            # Check if the token matches an OAuth token from storage
            try:
                from arc_memory.auth.linear import get_oauth_token_from_keyring
                oauth_token = get_oauth_token_from_keyring()
                if oauth_token and oauth_token.access_token == linear_token:
                    is_oauth_token = True
                    logger.info("Using OAuth token for Linear API")
            except ImportError:
                logger.debug("Could not import OAuth functions, assuming API key")
            except Exception as e:
                logger.debug(f"Error checking OAuth token: {e}, assuming API key")

            # Initialize Linear client with appropriate token type
            # Avoid logging any part of the token for security
            logger.info(f"Initializing Linear client (OAuth: {is_oauth_token})")
            client = LinearGraphQLClient(linear_token, is_oauth_token=is_oauth_token)

            # First test connectivity with a simple viewer query
            try:
                logger.info("Testing Linear API connectivity with viewer query...")
                viewer_data = client.execute_query(VIEWER_QUERY)
                logger.info(f"Linear API connection successful. Authenticated as: {viewer_data.get('viewer', {}).get('name')}")
            except Exception as e:
                logger.error(f"Failed to connect to Linear API: {e}")
                raise IngestError(f"Failed to connect to Linear API: {e}")

            # Fetch issues
            nodes = []
            edges = []
            issue_count = 0
            cursor = None

            while True:
                # Fetch issues with pagination
                variables = {"cursor": cursor} if cursor else {}
                logger.info(f"Fetching Linear issues with cursor: {cursor}")
                data = client.execute_query(ISSUES_QUERY, variables)

                # Process issues
                issues = data["issues"]["nodes"]
                for issue in issues:
                    issue_id = f"linear:{issue['id']}"
                    issue_identifier = issue["identifier"]

                    # Create labels list
                    labels = []
                    if issue["labels"] and "nodes" in issue["labels"]:
                        for label in issue["labels"]["nodes"]:
                            labels.append(label["name"])

                    # Get state
                    state = "unknown"
                    if issue["state"]:
                        state = issue["state"]["name"]

                    # Parse timestamps
                    created_at = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
                    closed_at = None
                    if issue["archivedAt"]:
                        closed_at = datetime.fromisoformat(issue["archivedAt"].replace("Z", "+00:00"))

                    # Extract numeric part from issue identifier (e.g., "ARC-10" -> 10)
                    try:
                        issue_number = int(issue_identifier.split('-')[-1])
                    except (ValueError, IndexError):
                        logger.warning(f"Could not parse issue number from identifier: {issue_identifier}, using 0")
                        issue_number = 0

                    # Create issue node
                    issue_node = IssueNode(
                        id=issue_id,
                        type=NodeType.ISSUE,
                        title=issue["title"],
                        body=issue["description"],
                        ts=created_at,
                        number=issue_number,  # Use the extracted numeric part
                        state=state,
                        closed_at=closed_at,
                        labels=labels,
                        url=issue["url"],
                        extra={
                            "source": "linear",
                            "identifier": issue_identifier,  # Store the original identifier
                            "team": issue["team"]["key"] if issue["team"] else None,
                            "assignee": issue["assignee"]["name"] if issue["assignee"] else None,
                            "creator": issue["creator"]["name"] if issue["creator"] else None,
                        },
                    )
                    nodes.append(issue_node)
                    issue_count += 1

                    # Create edges to commits and PRs based on branch naming or commit messages
                    # This will be done by scanning Git commits and PRs for references to the issue
                    # Format: TEAM-123 or team/TEAM-123

                    # For now, we'll just create a placeholder edge to the repo
                    edge = Edge(
                        src=issue_id,
                        dst=f"repo:{repo_path.name}",
                        rel=EdgeRel.MENTIONS,
                        properties={
                            "source": "linear",
                        },
                    )
                    edges.append(edge)

                # Check if there are more pages
                page_info = data["issues"]["pageInfo"]
                if not page_info["hasNextPage"]:
                    break

                cursor = page_info["endCursor"]
                logger.info(f"Fetched {len(issues)} issues, continuing to next page")

            # Create metadata
            metadata = {
                "issue_count": issue_count,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Processed {issue_count} Linear issues")
            return nodes, edges, metadata
        except Exception as e:
            logger.exception("Unexpected error during Linear ingestion")
            raise IngestError(f"Failed to ingest Linear issues: {e}")


def extract_linear_issue_references(text: str) -> List[str]:
    """Extract Linear issue references from text.

    Args:
        text: The text to extract references from.

    Returns:
        A list of Linear issue identifiers.
    """
    # Match patterns like TEAM-123 or team/TEAM-123
    pattern = r'([A-Z0-9]+-[0-9]+)'
    matches = re.findall(pattern, text)
    return matches
