"""GitHub data fetching for Arc Memory."""

import logging
import time
from datetime import datetime, timezone
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
                variables = {"owner": owner, "repo": repo}
            else:
                logger.info("Fetching all PRs")
                query = PULL_REQUESTS_QUERY
                variables = {"owner": owner, "repo": repo}

            # Execute the paginated query
            prs = await self.graphql_client.paginate_query(
                query, variables, ["repository", "pullRequests"]
            )

            # If we have a since parameter, filter the results manually
            if since:
                filtered_prs = []
                for pr in prs:
                    updated_at = datetime.fromisoformat(pr["updatedAt"].replace("Z", "+00:00"))

                    # Ensure both datetimes are timezone-aware for accurate comparison
                    if since.tzinfo is None:
                        # If since is naive, make it timezone-aware with UTC
                        since_aware = since.replace(tzinfo=timezone.utc)
                    else:
                        since_aware = since

                    if updated_at >= since_aware:
                        filtered_prs.append(pr)
                prs = filtered_prs

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
                variables = {"owner": owner, "repo": repo}
            else:
                logger.info("Fetching all issues")
                query = ISSUES_QUERY
                variables = {"owner": owner, "repo": repo}

            # Execute the paginated query
            issues = await self.graphql_client.paginate_query(
                query, variables, ["repository", "issues"]
            )

            # If we have a since parameter, filter the results manually
            if since:
                filtered_issues = []
                for issue in issues:
                    updated_at = datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00"))

                    # Ensure both datetimes are timezone-aware for accurate comparison
                    if since.tzinfo is None:
                        # If since is naive, make it timezone-aware with UTC
                        since_aware = since.replace(tzinfo=timezone.utc)
                    else:
                        since_aware = since

                    if updated_at >= since_aware:
                        filtered_issues.append(issue)
                issues = filtered_issues

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

            # Fetch PR commits
            commits = self.rest_client.get_commits_for_pr(owner, repo, pr_number)

            # Fetch review comments (inline comments)
            review_comments = self.rest_client.get_review_comments(owner, repo, pr_number)

            return {
                "files": files,
                "reviews": reviews,
                "comments": comments,
                "commits": commits,
                "review_comments": review_comments,
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

            # Fetch issue events
            events = self.rest_client.get_issue_events(owner, repo, issue_number)

            # Fetch issue timeline
            timeline = self.rest_client.get_issue_timeline(owner, repo, issue_number)

            return {
                "comments": comments,
                "events": events,
                "timeline": timeline,
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

        # Add commit information
        if details and "commits" in details:
            extra["commits"] = [
                {
                    "sha": commit.get("sha"),
                    "message": commit.get("commit", {}).get("message"),
                    "author": commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name"),
                    "url": commit.get("html_url"),
                }
                for commit in details["commits"]
            ]

        # Add review comment information (inline comments)
        if details and "review_comments" in details:
            extra["review_comments"] = [
                {
                    "author": comment.get("user", {}).get("login"),
                    "body": comment.get("body"),
                    "created_at": comment.get("created_at"),
                    "path": comment.get("path"),
                    "position": comment.get("position"),
                    "diff_hunk": comment.get("diff_hunk"),
                }
                for comment in details["review_comments"]
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

        # Add events information
        if details and "events" in details:
            extra["events"] = [
                {
                    "event": event.get("event"),
                    "actor": event.get("actor", {}).get("login"),
                    "created_at": event.get("created_at"),
                    "label": event.get("label", {}).get("name") if event.get("label") else None,
                    "assignee": event.get("assignee", {}).get("login") if event.get("assignee") else None,
                }
                for event in details["events"]
            ]

        # Add timeline information
        if details and "timeline" in details:
            extra["timeline"] = [
                {
                    "event": item.get("event"),
                    "actor": item.get("actor", {}).get("login") if item.get("actor") else None,
                    "created_at": item.get("created_at"),
                    # Include additional fields based on event type
                    **({
                        "label": item.get("label", {}).get("name")
                    } if item.get("event") == "labeled" or item.get("event") == "unlabeled" else {}),
                    **({
                        "assignee": item.get("assignee", {}).get("login")
                    } if item.get("event") == "assigned" or item.get("event") == "unassigned" else {}),
                    **({
                        "milestone": item.get("milestone", {}).get("title")
                    } if item.get("event") == "milestoned" or item.get("event") == "demilestoned" else {}),
                    **({
                        "rename": {
                            "from": item.get("rename", {}).get("from"),
                            "to": item.get("rename", {}).get("to"),
                        }
                    } if item.get("event") == "renamed" else {}),
                    **({
                        "cross_reference": {
                            "source": item.get("source", {}).get("issue", {}).get("number"),
                            "type": "pr" if item.get("source", {}).get("issue", {}).get("pull_request") else "issue",
                        }
                    } if item.get("event") == "cross-referenced" else {}),
                }
                for item in details["timeline"]
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

    def fetch_pr_details_batch(
        self, owner: str, repo: str, pr_numbers: List[int], batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """Fetch details for multiple PRs in batches.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_numbers: List of PR numbers.
            batch_size: Number of PRs to process in each batch.

        Returns:
            A list of PR details, one for each PR number.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error fetching the data.
        """
        logger.info(f"Fetching details for {len(pr_numbers)} PRs in {owner}/{repo}")

        results = []

        # Process PRs in batches
        for i in range(0, len(pr_numbers), batch_size):
            batch = pr_numbers[i:i + batch_size]
            batch_results = []

            # Get basic PR details in batch
            pr_details_batch = self.rest_client.get_pr_details_batch(owner, repo, batch)

            # Process each PR in the batch
            for j, pr_number in enumerate(batch):
                try:
                    # Get the basic PR details
                    pr_basic = pr_details_batch[j]
                    if pr_basic is None:
                        logger.warning(f"Failed to fetch basic details for PR #{pr_number}")
                        results.append(None)
                        continue

                    # Fetch additional details
                    details = self.fetch_pr_details_sync(owner, repo, pr_number)

                    # Combine basic details and additional details
                    combined_details = {
                        **pr_basic,
                        "files": details.get("files", []),
                        "reviews": details.get("reviews", []),
                        "comments": details.get("comments", []),
                        "commits": details.get("commits", []),
                        "review_comments": details.get("review_comments", []),
                    }

                    batch_results.append(combined_details)
                except Exception as e:
                    logger.error(f"Error processing PR #{pr_number}: {e}")
                    batch_results.append(None)

            # Add batch results to overall results
            results.extend(batch_results)

            # Log progress
            logger.info(f"Processed {min(i + batch_size, len(pr_numbers))}/{len(pr_numbers)} PRs")

            # Sleep between batches if not the last batch
            if i + batch_size < len(pr_numbers):
                time.sleep(1.0)

        return results

    def fetch_issue_details_batch(
        self, owner: str, repo: str, issue_numbers: List[int], batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """Fetch details for multiple issues in batches.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_numbers: List of issue numbers.
            batch_size: Number of issues to process in each batch.

        Returns:
            A list of issue details, one for each issue number.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error fetching the data.
        """
        logger.info(f"Fetching details for {len(issue_numbers)} issues in {owner}/{repo}")

        results = []

        # Process issues in batches
        for i in range(0, len(issue_numbers), batch_size):
            batch = issue_numbers[i:i + batch_size]
            batch_results = []

            # Get basic issue details in batch
            issue_details_batch = self.rest_client.get_issue_details_batch(owner, repo, batch)

            # Process each issue in the batch
            for j, issue_number in enumerate(batch):
                try:
                    # Get the basic issue details
                    issue_basic = issue_details_batch[j]
                    if issue_basic is None:
                        logger.warning(f"Failed to fetch basic details for issue #{issue_number}")
                        results.append(None)
                        continue

                    # Fetch additional details
                    details = self.fetch_issue_details_sync(owner, repo, issue_number)

                    # Combine basic details and additional details
                    combined_details = {
                        **issue_basic,
                        "comments": details.get("comments", []),
                        "events": details.get("events", []),
                        "timeline": details.get("timeline", []),
                    }

                    batch_results.append(combined_details)
                except Exception as e:
                    logger.error(f"Error processing issue #{issue_number}: {e}")
                    batch_results.append(None)

            # Add batch results to overall results
            results.extend(batch_results)

            # Log progress
            logger.info(f"Processed {min(i + batch_size, len(issue_numbers))}/{len(issue_numbers)} issues")

            # Sleep between batches if not the last batch
            if i + batch_size < len(issue_numbers):
                time.sleep(1.0)

        return results
