"""GitHub data fetching for Arc Memory."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from arc_memory.errors import GitHubAuthError, IngestError
from arc_memory.ingest.github_graphql import (
    GitHubGraphQLClient,
    PULL_REQUESTS_QUERY,
    ISSUES_QUERY,
    UPDATED_PRS_QUERY,
    UPDATED_ISSUES_QUERY,
)
from arc_memory.ingest.github_rest import GitHubRESTClient
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, EdgeRel, IssueNode, NodeType, PRNode

logger = get_logger(__name__)


class GitHubFetcher:
    """Fetcher for GitHub data using GraphQL and REST APIs."""

    def __init__(self, token: str):
        """Initialize the GitHub fetcher.

        Args:
            token: GitHub token to use for API calls.
        """
        self.token = token
        self.graphql_client = GitHubGraphQLClient(token)
        self.rest_client = GitHubRESTClient(token)

    async def fetch_pull_requests(
        self, owner: str, repo: str, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch pull requests from GitHub.

        Args:
            owner: Repository owner.
            repo: Repository name.
            since: Only fetch PRs updated since this time.

        Returns:
            A list of pull request data.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error fetching the data.
        """
        logger.info(f"Fetching pull requests for {owner}/{repo}")
        
        try:
            # Determine which query to use based on whether we have a since parameter
            if since:
                logger.info(f"Fetching PRs updated since {since.isoformat()}")
                query = UPDATED_PRS_QUERY
                variables = {"owner": owner, "repo": repo, "since": since.isoformat()}
            else:
                logger.info("Fetching all PRs")
                query = PULL_REQUESTS_QUERY
                variables = {"owner": owner, "repo": repo}
            
            # Execute the paginated query
            prs = await self.graphql_client.paginate_query(
                query, variables, ["repository", "pullRequests"]
            )
            
            logger.info(f"Fetched {len(prs)} pull requests")
            return prs
        except GitHubAuthError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            logger.exception(f"Error fetching pull requests: {e}")
            raise IngestError(f"Failed to fetch pull requests: {e}")

    async def fetch_issues(
        self, owner: str, repo: str, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch issues from GitHub.

        Args:
            owner: Repository owner.
            repo: Repository name.
            since: Only fetch issues updated since this time.

        Returns:
            A list of issue data.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error fetching the data.
        """
        logger.info(f"Fetching issues for {owner}/{repo}")
        
        try:
            # Determine which query to use based on whether we have a since parameter
            if since:
                logger.info(f"Fetching issues updated since {since.isoformat()}")
                query = UPDATED_ISSUES_QUERY
                variables = {"owner": owner, "repo": repo, "since": since.isoformat()}
            else:
                logger.info("Fetching all issues")
                query = ISSUES_QUERY
                variables = {"owner": owner, "repo": repo}
            
            # Execute the paginated query
            issues = await self.graphql_client.paginate_query(
                query, variables, ["repository", "issues"]
            )
            
            logger.info(f"Fetched {len(issues)} issues")
            return issues
        except GitHubAuthError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            logger.exception(f"Error fetching issues: {e}")
            raise IngestError(f"Failed to fetch issues: {e}")

    async def fetch_pr_details(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """Fetch additional details for a pull request using REST API.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            Additional PR details.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error fetching the data.
        """
        logger.info(f"Fetching details for PR #{pr_number} in {owner}/{repo}")
        
        try:
            # Fetch PR files
            files = self.rest_client.get_pr_files(owner, repo, pr_number)
            
            # Fetch PR reviews
            reviews = self.rest_client.get_pr_reviews(owner, repo, pr_number)
            
            # Fetch PR comments
            comments = self.rest_client.get_pr_comments(owner, repo, pr_number)
            
            return {
                "files": files,
                "reviews": reviews,
                "comments": comments,
            }
        except GitHubAuthError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            logger.exception(f"Error fetching PR details: {e}")
            raise IngestError(f"Failed to fetch PR details: {e}")

    async def fetch_issue_details(
        self, owner: str, repo: str, issue_number: int
    ) -> Dict[str, Any]:
        """Fetch additional details for an issue using REST API.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            Additional issue details.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error fetching the data.
        """
        logger.info(f"Fetching details for issue #{issue_number} in {owner}/{repo}")
        
        try:
            # Fetch issue comments
            comments = self.rest_client.get_issue_comments(owner, repo, issue_number)
            
            return {
                "comments": comments,
            }
        except GitHubAuthError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            logger.exception(f"Error fetching issue details: {e}")
            raise IngestError(f"Failed to fetch issue details: {e}")

    def create_pr_node(self, pr_data: Dict[str, Any], details: Dict[str, Any]) -> PRNode:
        """Create a PRNode from PR data.

        Args:
            pr_data: Pull request data from GraphQL.
            details: Additional details from REST API.

        Returns:
            A PRNode object.
        """
        # Extract basic PR information
        pr_id = pr_data["id"]
        pr_number = pr_data["number"]
        title = pr_data["title"]
        body = pr_data["body"] or ""
        state = pr_data["state"]
        created_at = datetime.fromisoformat(pr_data["createdAt"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(pr_data["updatedAt"].replace("Z", "+00:00"))
        url = pr_data["url"]
        
        # Extract author information
        author = pr_data.get("author", {})
        author_login = author.get("login") if author else None
        
        # Extract merge information
        merged_at = None
        if pr_data.get("mergedAt"):
            merged_at = datetime.fromisoformat(pr_data["mergedAt"].replace("Z", "+00:00"))
        
        merged_commit_sha = None
        if pr_data.get("mergeCommit", {}) and pr_data["mergeCommit"].get("oid"):
            merged_commit_sha = pr_data["mergeCommit"]["oid"]
        
        # Create extra data
        extra = {
            "author": author_login,
            "baseRefName": pr_data.get("baseRefName"),
            "headRefName": pr_data.get("headRefName"),
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
        }
        
        # Add file information
        if details and "files" in details:
            extra["files"] = [
                {
                    "filename": file["filename"],
                    "additions": file.get("additions", 0),
                    "deletions": file.get("deletions", 0),
                    "changes": file.get("changes", 0),
                }
                for file in details["files"]
            ]
        
        # Add review information
        if details and "reviews" in details:
            extra["reviews"] = [
                {
                    "author": review.get("user", {}).get("login"),
                    "state": review.get("state"),
                    "body": review.get("body"),
                    "submitted_at": review.get("submitted_at"),
                }
                for review in details["reviews"]
            ]
        
        # Add comment information
        if details and "comments" in details:
            extra["comments"] = [
                {
                    "author": comment.get("user", {}).get("login"),
                    "body": comment.get("body"),
                    "created_at": comment.get("created_at"),
                }
                for comment in details["comments"]
            ]
        
        # Create the PR node
        return PRNode(
            id=pr_id,
            title=title,
            body=body,
            ts=created_at,
            number=pr_number,
            state=state,
            merged_at=merged_at,
            merged_by=None,  # Not available in the current data
            merged_commit_sha=merged_commit_sha,
            url=url,
            extra=extra,
        )

    def create_issue_node(self, issue_data: Dict[str, Any], details: Dict[str, Any]) -> IssueNode:
        """Create an IssueNode from issue data.

        Args:
            issue_data: Issue data from GraphQL.
            details: Additional details from REST API.

        Returns:
            An IssueNode object.
        """
        # Extract basic issue information
        issue_id = issue_data["id"]
        issue_number = issue_data["number"]
        title = issue_data["title"]
        body = issue_data["body"] or ""
        state = issue_data["state"]
        created_at = datetime.fromisoformat(issue_data["createdAt"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(issue_data["updatedAt"].replace("Z", "+00:00"))
        url = issue_data["url"]
        
        # Extract author information
        author = issue_data.get("author", {})
        author_login = author.get("login") if author else None
        
        # Extract closed_at information
        closed_at = None
        if issue_data.get("closedAt"):
            closed_at = datetime.fromisoformat(issue_data["closedAt"].replace("Z", "+00:00"))
        
        # Extract labels
        labels = []
        if issue_data.get("labels", {}) and issue_data["labels"].get("nodes"):
            labels = [label["name"] for label in issue_data["labels"]["nodes"]]
        
        # Create extra data
        extra = {
            "author": author_login,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
        }
        
        # Add comment information
        if details and "comments" in details:
            extra["comments"] = [
                {
                    "author": comment.get("user", {}).get("login"),
                    "body": comment.get("body"),
                    "created_at": comment.get("created_at"),
                }
                for comment in details["comments"]
            ]
        
        # Create the issue node
        return IssueNode(
            id=issue_id,
            title=title,
            body=body,
            ts=created_at,
            number=issue_number,
            state=state,
            closed_at=closed_at,
            labels=labels,
            url=url,
            extra=extra,
        )

    def extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text.

        Args:
            text: Text to extract mentions from.

        Returns:
            A list of mentioned entities.
        """
        # This is a simple implementation that extracts GitHub-style mentions
        # A more sophisticated implementation would handle different types of mentions
        import re
        
        mentions = []
        
        # Extract GitHub-style mentions (@username)
        username_pattern = r'@([a-zA-Z0-9_-]+)'
        username_mentions = re.findall(username_pattern, text)
        mentions.extend(username_mentions)
        
        # Extract issue/PR references (#123)
        issue_pattern = r'#(\d+)'
        issue_mentions = re.findall(issue_pattern, text)
        mentions.extend([f"#{num}" for num in issue_mentions])
        
        return mentions

    def create_mention_edges(
        self, source_id: str, text: str, repo_issues: List[Dict[str, Any]], repo_prs: List[Dict[str, Any]]
    ) -> List[Edge]:
        """Create mention edges from text.

        Args:
            source_id: ID of the source node.
            text: Text to extract mentions from.
            repo_issues: List of repository issues.
            repo_prs: List of repository PRs.

        Returns:
            A list of mention edges.
        """
        edges = []
        mentions = self.extract_mentions(text)
        
        # Create a mapping of issue/PR numbers to IDs
        issue_map = {f"#{issue['number']}": issue["id"] for issue in repo_issues}
        pr_map = {f"#{pr['number']}": pr["id"] for pr in repo_prs}
        
        # Create edges for each mention
        for mention in mentions:
            if mention in issue_map:
                # This is an issue mention
                edges.append(
                    Edge(
                        src=source_id,
                        dst=issue_map[mention],
                        rel=EdgeRel.MENTIONS,
                        properties={"type": "issue_reference"},
                    )
                )
            elif mention in pr_map:
                # This is a PR mention
                edges.append(
                    Edge(
                        src=source_id,
                        dst=pr_map[mention],
                        rel=EdgeRel.MENTIONS,
                        properties={"type": "pr_reference"},
                    )
                )
            # We could also handle user mentions here if needed
        
        return edges

    def fetch_pull_requests_sync(
        self, owner: str, repo: str, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for fetch_pull_requests."""
        import asyncio
        
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.fetch_pull_requests(owner, repo, since))
        finally:
            loop.close()

    def fetch_issues_sync(
        self, owner: str, repo: str, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for fetch_issues."""
        import asyncio
        
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.fetch_issues(owner, repo, since))
        finally:
            loop.close()

    def fetch_pr_details_sync(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """Synchronous wrapper for fetch_pr_details."""
        import asyncio
        
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.fetch_pr_details(owner, repo, pr_number))
        finally:
            loop.close()

    def fetch_issue_details_sync(
        self, owner: str, repo: str, issue_number: int
    ) -> Dict[str, Any]:
        """Synchronous wrapper for fetch_issue_details."""
        import asyncio
        
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.fetch_issue_details(owner, repo, issue_number))
        finally:
            loop.close()
