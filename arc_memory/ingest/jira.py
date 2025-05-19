"""Jira ingestion for Arc Memory."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from arc_memory.auth.jira import get_jira_token, get_cloud_id_from_env
from arc_memory.errors import IngestError, JiraAuthError
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, IssueNode, Node, NodeType

logger = get_logger(__name__)

# Constants
JIRA_API_BASE_URL = "https://api.atlassian.com"
JIRA_API_VERSION = "3"  # Using v3 of the Jira Cloud REST API
USER_AGENT = "Arc-Memory/0.4.1"

# GraphQL queries are not used for Jira - using REST API instead
# But we define key endpoint paths

# API endpoints
def get_myself_endpoint() -> str:
    """Get the endpoint for fetching current user info."""
    return f"/rest/api/{JIRA_API_VERSION}/myself"

def get_projects_endpoint() -> str:
    """Get the endpoint for fetching projects."""
    return f"/rest/api/{JIRA_API_VERSION}/project/search"

def get_issues_endpoint() -> str:
    """Get the endpoint for searching issues."""
    return f"/rest/api/{JIRA_API_VERSION}/search"

def get_issue_endpoint(issue_key: str) -> str:
    """Get the endpoint for a specific issue."""
    return f"/rest/api/{JIRA_API_VERSION}/issue/{issue_key}"

def get_project_endpoint(project_key: str) -> str:
    """Get the endpoint for a specific project."""
    return f"/rest/api/{JIRA_API_VERSION}/project/{project_key}"


class JiraClient:
    """Client for interacting with the Jira API."""

    def __init__(self, token: str, cloud_id: str):
        """Initialize the Jira client.

        Args:
            token: Jira API token or OAuth token
            cloud_id: The Jira Cloud instance ID
        """
        self.token = token
        self.cloud_id = cloud_id
        self.base_url = f"{JIRA_API_BASE_URL}/ex/jira/{cloud_id}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

    def get_current_user(self) -> Dict[str, Any]:
        """Get information about the authenticated user.

        Returns:
            Dictionary containing user details

        Raises:
            JiraAuthError: If authentication fails
            IngestError: If the API request fails
        """
        endpoint = get_myself_endpoint()
        return self._make_request("GET", endpoint)

    def get_projects(self, start_at: int = 0, max_results: int = 50) -> Dict[str, Any]:
        """Get projects accessible to the authenticated user.

        Args:
            start_at: Index of the first project to return (for pagination)
            max_results: Maximum number of projects to return

        Returns:
            Dictionary containing projects information

        Raises:
            JiraAuthError: If authentication fails
            IngestError: If the API request fails
        """
        endpoint = get_projects_endpoint()
        params = {
            "startAt": start_at,
            "maxResults": max_results,
            "expand": "description,lead"
        }
        return self._make_request("GET", endpoint, params=params)

    def search_issues(
        self, 
        jql: str, 
        start_at: int = 0, 
        max_results: int = 50,
        fields: List[str] = None
    ) -> Dict[str, Any]:
        """Search for issues using JQL.

        Args:
            jql: JQL search string
            start_at: Index of the first issue to return (for pagination)
            max_results: Maximum number of issues to return
            fields: List of fields to include in the response

        Returns:
            Dictionary containing issues information

        Raises:
            JiraAuthError: If authentication fails
            IngestError: If the API request fails
        """
        endpoint = get_issues_endpoint()
        
        # Default fields to retrieve
        if fields is None:
            fields = [
                "summary", "description", "status", "issuetype", 
                "priority", "created", "updated", "assignee", 
                "reporter", "labels", "project", "fixVersions", 
                "comments", "issuelinks"
            ]
            
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ",".join(fields)
        }
        
        return self._make_request("GET", endpoint, params=params)

    def get_issue(self, issue_key: str, fields: List[str] = None) -> Dict[str, Any]:
        """Get details of a specific issue.

        Args:
            issue_key: The issue key (e.g., "PROJECT-123")
            fields: List of fields to include in the response

        Returns:
            Dictionary containing issue details

        Raises:
            JiraAuthError: If authentication fails
            IngestError: If the API request fails
        """
        endpoint = get_issue_endpoint(issue_key)
        
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
            
        return self._make_request("GET", endpoint, params=params)

    def get_project(self, project_key: str) -> Dict[str, Any]:
        """Get details of a specific project.

        Args:
            project_key: The project key (e.g., "PROJECT")

        Returns:
            Dictionary containing project details

        Raises:
            JiraAuthError: If authentication fails
            IngestError: If the API request fails
        """
        endpoint = get_project_endpoint(project_key)
        return self._make_request("GET", endpoint)

    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict[str, Any] = None, 
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make a request to the Jira API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: URL parameters
            data: Request body data

        Returns:
            Response data as dictionary

        Raises:
            JiraAuthError: If authentication fails
            IngestError: If the API request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            response = requests.request(
                method,
                url,
                headers=self.headers,
                params=params,
                json=data
            )
            
            # Handle authentication errors
            if response.status_code == 401:
                logger.error("Jira API authentication failed: Unauthorized (401)")
                raise JiraAuthError("Jira authentication failed: Invalid token or expired token")
                
            if response.status_code == 403:
                logger.error("Jira API authentication failed: Forbidden (403)")
                raise JiraAuthError("Jira authentication failed: Insufficient permissions")
            
            # Handle rate limit errors (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limit reached. Retry after {retry_after} seconds")
                # In a real-world scenario, we would implement backoff here
                raise IngestError(f"Jira API rate limit exceeded. Retry after {retry_after} seconds")
            
            # Handle other HTTP errors
            response.raise_for_status()
            
            # Parse response JSON
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Jira API request failed: {e}")
            
            # Handle connection errors
            if isinstance(e, requests.exceptions.ConnectionError):
                raise IngestError(f"Failed to connect to Jira API: {e}. Please check your internet connection.")
                
            # Handle timeout errors
            if isinstance(e, requests.exceptions.Timeout):
                raise IngestError(f"Jira API request timed out: {e}. Please try again later.")
                
            # Handle other request errors
            raise IngestError(f"Jira API request failed: {e}")
            
        except ValueError as e:
            logger.error(f"Failed to parse Jira API response: {e}")
            raise IngestError(f"Failed to parse Jira API response: {e}")


class JiraIngestor:
    """Ingestor plugin for Jira projects and issues."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "jira"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return [NodeType.ISSUE]  # For now, just use the ISSUE node type

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MENTIONS, EdgeRel.DEPENDS_ON]  # Basic edge types for Jira

    def ingest(
        self,
        repo_path: Path = None,
        token: Optional[str] = None,
        cloud_id: Optional[str] = None,
        project_keys: Optional[List[str]] = None,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest Jira projects and issues.

        Args:
            repo_path: Path to the repository (optional, used for creating edges)
            token: Jira token to use for API calls.
            cloud_id: The Jira Cloud instance ID
            last_processed: Metadata from the last build for incremental processing.

        Returns:
            A tuple of (nodes, edges, metadata).

        Raises:
            IngestError: If there's an error during ingestion.
        """
        logger.info("Ingesting Jira projects and issues")
        
        # For incremental builds, log and use last processed timestamp
        if last_processed:
            logger.info("Performing incremental build")
            last_updated = last_processed.get("last_updated")
            if last_updated:
                logger.info(f"Processing issues updated since {last_updated}")

        try:
            # Get Jira token
            jira_token = get_jira_token(token, allow_failure=True)
            if not jira_token:
                logger.warning("No Jira token found. Skipping Jira ingestion.")
                return [], [], {"issue_count": 0, "timestamp": datetime.now().isoformat()}

            # Get Cloud ID - either from parameters, environment, or fail
            if not cloud_id:
                cloud_id = get_cloud_id_from_env()
                
            if not cloud_id:
                logger.warning("No Jira Cloud ID found. Skipping Jira ingestion.")
                return [], [], {"issue_count": 0, "timestamp": datetime.now().isoformat()}
                
            logger.info(f"Using Jira Cloud ID: {cloud_id}")

            # Initialize Jira client
            client = JiraClient(jira_token, cloud_id)
            
            # Verify connection by fetching current user info
            try:
                user_data = client.get_current_user()
                logger.info(f"Connected to Jira as: {user_data.get('displayName', 'Unknown User')}")
            except Exception as e:
                logger.error(f"Failed to connect to Jira API: {e}")
                raise IngestError(f"Failed to connect to Jira API: {e}")

            # Initialize collections for nodes and edges
            nodes = []
            edges = []
            
            # Get projects first
            all_projects_fetched = self._fetch_all_projects(client)

            # Filter projects if project_keys is provided
            if project_keys:
                logger.info(f"Filtering projects by keys: {project_keys}")
                projects_to_process = []
                found_keys = set()
                for project in all_projects_fetched:
                    if project.get("key") in project_keys:
                        projects_to_process.append(project)
                        found_keys.add(project.get("key"))
                
                missing_keys = set(project_keys) - found_keys
                if missing_keys:
                    logger.warning(f"The following project keys were not found or accessible: {list(missing_keys)}")
                
                all_projects = projects_to_process
            else:
                all_projects = all_projects_fetched

            if not all_projects:
                if project_keys:
                    logger.warning("No projects found matching the provided project keys. Skipping Jira ingestion for issues.")
                else:
                    logger.warning("No projects found for this Jira instance. Skipping Jira ingestion for issues.")
                return [], [], {
                    "issue_count": 0, 
                    "project_count": 0, 
                    "last_updated": datetime.now().isoformat(),
                    "timestamp": datetime.now().isoformat()
                }
            
            # Process projects
            project_nodes = self._process_projects(all_projects)
            nodes.extend(project_nodes)
            
            # For each project, fetch and process issues
            for project in all_projects:
                project_key = project.get("key")
                
                # Build JQL for this project
                jql = f"project = {project_key}"
                
                # If this is an incremental build, only get issues updated since last run
                if last_processed and "last_updated" in last_processed:
                    jql += f" AND updated >= '{last_processed['last_updated']}'"
                
                # Get all issues
                all_issues = self._fetch_all_issues(client, jql)
                
                # Process issues and create issue-to-project edges
                issue_nodes, project_edges = self._process_issues(all_issues, project_key)
                nodes.extend(issue_nodes)
                edges.extend(project_edges)
                
                # Create issue-to-issue relationship edges
                issue_edges = self._process_issue_links(all_issues)
                edges.extend(issue_edges)
                
                # If repo_path provided, create edges between issues and repo
                if repo_path:
                    repo_edges = self._create_repo_edges(issue_nodes, repo_path)
                    edges.extend(repo_edges)
            
            # Create metadata with timestamp for incremental builds
            metadata = {
                "issue_count": len([n for n in nodes if n.type == NodeType.ISSUE]),
                "project_count": len(project_nodes), # Count based on processed project nodes
                "last_updated": datetime.now().isoformat(),
                "timestamp": datetime.now().isoformat(),
            }
            
            logger.info(f"Processed {metadata['issue_count']} Jira issues from {metadata['project_count']} projects")
            return nodes, edges, metadata
            
        except Exception as e:
            logger.exception("Unexpected error during Jira ingestion")
            raise IngestError(f"Failed to ingest Jira data: {e}")

    def _fetch_all_projects(self, client: JiraClient) -> List[Dict[str, Any]]:
        """Fetch all accessible projects with pagination.
        
        Args:
            client: The JiraClient to use
            
        Returns:
            List of project data dictionaries
        """
        projects = []
        start_at = 0
        max_results = 50
        
        while True:
            response = client.get_projects(start_at=start_at, max_results=max_results)
            batch = response.get("values", [])
            
            if not batch:
                break
                
            projects.extend(batch)
            
            # Check if we've received all projects
            total = response.get("total", 0)
            if len(projects) >= total:
                break
                
            # Update start_at for next page
            start_at += len(batch)
            logger.info(f"Fetched {len(projects)}/{total} projects")
            
        return projects

    def _fetch_all_issues(self, client: JiraClient, jql: str) -> List[Dict[str, Any]]:
        """Fetch all issues matching JQL with pagination.
        
        Args:
            client: The JiraClient to use
            jql: JQL query to filter issues
            
        Returns:
            List of issue data dictionaries
        """
        issues = []
        start_at = 0
        max_results = 50
        
        while True:
            response = client.search_issues(jql=jql, start_at=start_at, max_results=max_results)
            batch = response.get("issues", [])
            
            if not batch:
                break
                
            issues.extend(batch)
            
            # Check if we've received all issues
            total = response.get("total", 0)
            if len(issues) >= total:
                break
                
            # Update start_at for next page
            start_at += len(batch)
            logger.info(f"Fetched {len(issues)}/{total} issues for JQL: {jql}")
            
        return issues

    def _process_projects(self, projects: List[Dict[str, Any]]) -> List[Node]:
        """Process project data into nodes.
        
        Args:
            projects: List of project data from Jira API
            
        Returns:
            List of project Node objects
        """
        project_nodes = []
        
        for project in projects:
            # Extract project details
            project_id = project.get("id")
            project_key = project.get("key")
            project_name = project.get("name")
            description = project.get("description")
            
            # Create node ID
            node_id = f"jira:project:{project_key}"
            
            # Extract lead (project owner) if available
            lead = {}
            if "lead" in project:
                lead = {
                    "displayName": project["lead"].get("displayName"),
                    "accountId": project["lead"].get("accountId")
                }
            
            # Create a project Node using a custom type
            # Note: We're not using a built-in NodeType since there's no PROJECT type
            # In a real implementation, you would define a ProjectNode class
            project_node = Node(
                id=node_id,
                type="jira_project",  # Custom type - not in NodeType enum
                title=project_name,
                body=description,
                ts=None,  # No creation timestamp in the API response
                metadata={
                    "source": "jira",
                    "project_id": project_id,
                    "project_key": project_key,
                    "lead": lead,
                    "url": f"https://your-domain.atlassian.net/projects/{project_key}"  # Template URL
                }
            )
            
            project_nodes.append(project_node)
            
        return project_nodes

    def _process_issues(
        self, 
        issues: List[Dict[str, Any]], 
        project_key: str
    ) -> Tuple[List[Node], List[Edge]]:
        """Process issue data into nodes and create edges to projects.
        
        Args:
            issues: List of issue data from Jira API
            project_key: The project key these issues belong to
            
        Returns:
            Tuple of (issue nodes, project edges)
        """
        issue_nodes = []
        project_edges = []
        
        for issue in issues:
            # Extract issue fields
            issue_key = issue.get("key")
            fields = issue.get("fields", {})
            
            # Extract basic issue details
            summary = fields.get("summary", "")
            description = fields.get("description", "")
            
            # Parse timestamps
            created = None
            if "created" in fields:
                try:
                    created = datetime.fromisoformat(fields["created"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse created timestamp for issue {issue_key}")
            
            updated = None
            if "updated" in fields:
                try:
                    updated = datetime.fromisoformat(fields["updated"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse updated timestamp for issue {issue_key}")
            
            # Extract other fields
            status_name = fields.get("status", {}).get("name", "Unknown")
            issue_type = fields.get("issuetype", {}).get("name", "Unknown")
            priority = fields.get("priority", {}).get("name", "Unknown")
            
            # Extract assignee
            assignee = None
            if fields.get("assignee"):
                assignee = fields["assignee"].get("displayName", "Unknown")
            
            # Extract reporter
            reporter = None
            if fields.get("reporter"):
                reporter = fields["reporter"].get("displayName", "Unknown")
            
            # Extract labels
            labels = fields.get("labels", [])
            
            # Extract numeric part from issue key (e.g., "PROJECT-10" -> 10)
            try:
                issue_number = int(issue_key.split('-')[-1])
            except (ValueError, IndexError):
                logger.warning(f"Could not parse issue number from key: {issue_key}, using 0")
                issue_number = 0
            
            # Create issue node
            node_id = f"jira:issue:{issue_key}"
            
            issue_node = IssueNode(
                id=node_id,
                type=NodeType.ISSUE,
                title=summary,
                body=description,
                ts=created,
                created_at=created,
                updated_at=updated,
                number=issue_number,
                state=status_name,
                labels=labels,
                url=f"https://your-domain.atlassian.net/browse/{issue_key}",  # Template URL
                metadata={
                    "source": "jira",
                    "issue_key": issue_key,
                    "issue_type": issue_type,
                    "priority": priority,
                    "assignee": assignee,
                    "reporter": reporter,
                    "project_key": project_key
                }
            )
            
            issue_nodes.append(issue_node)
            
            # Create edge from issue to project
            project_edge = Edge(
                src=node_id,
                dst=f"jira:project:{project_key}",
                rel=EdgeRel.PART_OF,
                properties={
                    "source": "jira"
                }
            )
            
            project_edges.append(project_edge)
            
        return issue_nodes, project_edges

    def _process_issue_links(self, issues: List[Dict[str, Any]]) -> List[Edge]:
        """Process issue links into edges.
        
        Args:
            issues: List of issue data from Jira API
            
        Returns:
            List of issue relationship Edges
        """
        edges = []
        
        for issue in issues:
            issue_key = issue.get("key")
            source_id = f"jira:issue:{issue_key}"
            
            # Extract issuelinks field
            fields = issue.get("fields", {})
            issue_links = fields.get("issuelinks", [])
            
            for link in issue_links:
                # Extract link type
                link_type = link.get("type", {}).get("name", "relates to")
                inward = link.get("type", {}).get("inward", "relates to")
                outward = link.get("type", {}).get("outward", "relates to")
                
                # Map Jira link types to EdgeRel types
                rel_type = self._map_link_type_to_edge_rel(link_type, inward, outward)
                
                # Process inward links
                if "inwardIssue" in link:
                    target_key = link["inwardIssue"].get("key")
                    target_id = f"jira:issue:{target_key}"
                    
                    # Create edge
                    edge = Edge(
                        src=source_id,
                        dst=target_id,
                        rel=rel_type,
                        properties={
                            "source": "jira",
                            "link_type": link_type,
                            "direction": "inward",
                            "description": inward
                        }
                    )
                    
                    edges.append(edge)
                
                # Process outward links
                if "outwardIssue" in link:
                    target_key = link["outwardIssue"].get("key")
                    target_id = f"jira:issue:{target_key}"
                    
                    # Create edge
                    edge = Edge(
                        src=source_id,
                        dst=target_id,
                        rel=rel_type,
                        properties={
                            "source": "jira",
                            "link_type": link_type,
                            "direction": "outward",
                            "description": outward
                        }
                    )
                    
                    edges.append(edge)
            
        return edges

    def _map_link_type_to_edge_rel(self, link_type: str, inward: str, outward: str) -> str:
        """Map Jira link types to EdgeRel types.
        
        Args:
            link_type: The Jira link type name
            inward: The inward description
            outward: The outward description
            
        Returns:
            EdgeRel type
        """
        # Map common Jira link types to EdgeRel types
        link_type_lower = link_type.lower()
        
        if "blocks" in link_type_lower or "is blocked by" in inward.lower() or "blocks" in outward.lower():
            return EdgeRel.BLOCKS
        
        if "depends" in link_type_lower or "depends on" in inward.lower() or "is depended on by" in outward.lower():
            return EdgeRel.DEPENDS_ON
            
        if "relates" in link_type_lower:
            return EdgeRel.MENTIONS
            
        # Default
        return EdgeRel.MENTIONS

    def _create_repo_edges(self, issue_nodes: List[Node], repo_path: Path) -> List[Edge]:
        """Create edges between issues and repository.
        
        Args:
            issue_nodes: List of issue nodes
            repo_path: Path to the repository
            
        Returns:
            List of edges between issues and repository
        """
        edges = []
        
        for node in issue_nodes:
            edge = Edge(
                src=node.id,
                dst=f"repo:{repo_path.name}",
                rel=EdgeRel.MENTIONS,
                properties={
                    "source": "jira"
                }
            )
            
            edges.append(edge)
            
        return edges


def extract_jira_issue_references(text: str) -> List[str]:
    """Extract Jira issue references from text.

    Args:
        text: The text to extract references from.

    Returns:
        A list of Jira issue identifiers.
    """
    # Match patterns like PROJECT-123
    pattern = r'([A-Z0-9]+-[0-9]+)'
    matches = re.findall(pattern, text)
    return matches