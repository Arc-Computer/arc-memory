"""Linear ingestion for Arc Memory."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from pydantic import BaseModel

from arc_memory.auth.linear import get_linear_token
from arc_memory.errors import IngestError, LinearAuthError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, IssueNode, Node, NodeType

logger = get_logger(__name__)

# Constants
LINEAR_API_URL = "https://api.linear.app/graphql"
USER_AGENT = "Arc-Memory/0.2.2"

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


class LinearGraphQLClient:
    """GraphQL client for Linear API."""

    def __init__(self, token: str):
        """Initialize the GraphQL client.

        Args:
            token: Linear token to use for API calls.
        """
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

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
        if variables is None:
            variables = {}

        try:
            response = requests.post(
                LINEAR_API_URL,
                headers=self.headers,
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                error_message = data["errors"][0]["message"]
                logger.error(f"Linear GraphQL error: {error_message}")
                if "authentication" in error_message.lower():
                    raise LinearAuthError(f"Linear authentication failed: {error_message}")
                raise IngestError(f"Linear GraphQL error: {error_message}")

            return data["data"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Linear API request failed: {e}")
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

            # Initialize Linear client
            client = LinearGraphQLClient(linear_token)

            # Fetch issues
            nodes = []
            edges = []
            issue_count = 0
            cursor = None

            while True:
                # Fetch issues with pagination
                variables = {"cursor": cursor} if cursor else {}
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

                    # Create issue node
                    issue_node = IssueNode(
                        id=issue_id,
                        type=NodeType.ISSUE,
                        title=issue["title"],
                        body=issue["description"],
                        ts=created_at,
                        number=issue_identifier,
                        state=state,
                        closed_at=closed_at,
                        labels=labels,
                        url=issue["url"],
                        extra={
                            "source": "linear",
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
