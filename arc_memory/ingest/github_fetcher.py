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
            Additional PR details or None if the PR details couldn't be fetched.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
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
            # Return None instead of raising an exception
            return None

    async def fetch_issue_details(
        self, owner: str, repo: str, issue_number: int
    ) -> Dict[str, Any]:
        """Fetch additional details for an issue using REST API.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            Additional issue details or None if the issue details couldn't be fetched.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
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
            # Return None instead of raising an exception
            return None

    def create_pr_node(self, pr_data: Dict[str, Any], details: Optional[Dict[str, Any]]) -> PRNode:
        """Create a PRNode from PR data.

        Args:
            pr_data: Pull request data from GraphQL.
            details: Additional details from REST API, may be None.

        Returns:
            A PRNode object.
        """
        try:
            # Validate pr_data
            if not pr_data or not isinstance(pr_data, dict):
                logger.error(f"Invalid PR data: {pr_data}")
                raise ValueError("Invalid PR data format")

            # Extract basic PR information with safety checks
            pr_id = pr_data.get("id")
            if not pr_id:
                logger.error(f"PR data missing ID: {pr_data}")
                raise ValueError("PR data missing ID")

            pr_number = pr_data.get("number")
            title = pr_data.get("title", "Untitled PR")
            body = pr_data.get("body") or ""
            state = pr_data.get("state", "unknown")
            url = pr_data.get("url", "")

            # Parse timestamps with error handling
            created_at = None
            updated_at = None

            if pr_data.get("createdAt"):
                try:
                    created_at = datetime.fromisoformat(pr_data["createdAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing createdAt for PR #{pr_number}: {e}")
                    created_at = datetime.now()  # Fallback to current time

            if pr_data.get("updatedAt"):
                try:
                    updated_at = datetime.fromisoformat(pr_data["updatedAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing updatedAt for PR #{pr_number}: {e}")
                    updated_at = datetime.now()  # Fallback to current time

            if not created_at:
                created_at = datetime.now()  # Fallback if no created_at timestamp

            if not updated_at:
                updated_at = created_at  # Fallback if no updated_at timestamp

            # Extract author information safely
            author = pr_data.get("author", {})
            author_login = author.get("login") if author and isinstance(author, dict) else None

            # Extract merge information safely
            merged_at = None
            if pr_data.get("mergedAt"):
                try:
                    merged_at = datetime.fromisoformat(pr_data["mergedAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing mergedAt for PR #{pr_number}: {e}")

            merged_commit_sha = None
            merge_commit = pr_data.get("mergeCommit", {})
            if merge_commit and isinstance(merge_commit, dict) and merge_commit.get("oid"):
                merged_commit_sha = merge_commit["oid"]

            # Create extra data
            extra = {
                "author": author_login,
                "baseRefName": pr_data.get("baseRefName"),
                "headRefName": pr_data.get("headRefName"),
                "created_at": created_at.isoformat(),
                "updated_at": updated_at.isoformat(),
            }

            # Safely add details data
            if details is not None and isinstance(details, dict):
                # Add file information
                if "files" in details and isinstance(details["files"], list):
                    extra["files"] = []
                    for file in details["files"]:
                        if file and isinstance(file, dict):
                            extra["files"].append({
                                "filename": file.get("filename", "unknown"),
                                "additions": file.get("additions", 0),
                                "deletions": file.get("deletions", 0),
                                "changes": file.get("changes", 0),
                            })

                # Add review information
                if "reviews" in details and isinstance(details["reviews"], list):
                    extra["reviews"] = []
                    for review in details["reviews"]:
                        if review and isinstance(review, dict):
                            user = review.get("user", {})
                            extra["reviews"].append({
                                "author": user.get("login") if user and isinstance(user, dict) else None,
                                "state": review.get("state"),
                                "body": review.get("body"),
                                "submitted_at": review.get("submitted_at"),
                            })

                # Add comment information
                if "comments" in details and isinstance(details["comments"], list):
                    extra["comments"] = []
                    for comment in details["comments"]:
                        if comment and isinstance(comment, dict):
                            user = comment.get("user", {})
                            extra["comments"].append({
                                "author": user.get("login") if user and isinstance(user, dict) else None,
                                "body": comment.get("body"),
                                "created_at": comment.get("created_at"),
                            })

                # Add commit information
                if "commits" in details and isinstance(details["commits"], list):
                    extra["commits"] = []
                    for commit in details["commits"]:
                        if commit and isinstance(commit, dict):
                            commit_data = commit.get("commit", {})
                            author_data = commit.get("author", {})
                            commit_author_data = commit_data.get("author", {}) if isinstance(commit_data, dict) else {}

                            author_name = None
                            if isinstance(author_data, dict) and author_data.get("login"):
                                author_name = author_data.get("login")
                            elif isinstance(commit_author_data, dict) and commit_author_data.get("name"):
                                author_name = commit_author_data.get("name")

                            extra["commits"].append({
                                "sha": commit.get("sha"),
                                "message": commit_data.get("message") if isinstance(commit_data, dict) else None,
                                "author": author_name,
                                "url": commit.get("html_url"),
                            })

                # Add review comment information (inline comments)
                if "review_comments" in details and isinstance(details["review_comments"], list):
                    extra["review_comments"] = []
                    for comment in details["review_comments"]:
                        if comment and isinstance(comment, dict):
                            user = comment.get("user", {})
                            extra["review_comments"].append({
                                "author": user.get("login") if user and isinstance(user, dict) else None,
                                "body": comment.get("body"),
                                "created_at": comment.get("created_at"),
                                "path": comment.get("path"),
                                "position": comment.get("position"),
                                "diff_hunk": comment.get("diff_hunk"),
                            })

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
        except Exception as e:
            logger.error(f"Error creating PR node for PR #{pr_data.get('number', 'unknown')}: {e}")
            # Create a minimal PR node with the available data
            try:
                pr_id = pr_data.get("id") if pr_data and isinstance(pr_data, dict) else f"pr:unknown-{datetime.now().timestamp()}"
                pr_number = pr_data.get("number") if pr_data and isinstance(pr_data, dict) else 0
                return PRNode(
                    id=pr_id,
                    title="Error Processing PR",
                    body=f"Error: {str(e)}",
                    ts=datetime.now(),
                    number=pr_number,
                    state="unknown",
                    url="",
                    extra={"error": str(e)},
                )
            except Exception as inner_e:
                logger.error(f"Critical error creating fallback PR node: {inner_e}")
                # Last resort fallback
                return PRNode(
                    id=f"pr:error-{datetime.now().timestamp()}",
                    title="Error Processing PR",
                    body="Critical error occurred",
                    ts=datetime.now(),
                    number=0,
                    state="error",
                    url="",
                    extra={"critical_error": True},
                )

    def create_issue_node(self, issue_data: Dict[str, Any], details: Optional[Dict[str, Any]]) -> IssueNode:
        """Create an IssueNode from issue data.

        Args:
            issue_data: Issue data from GraphQL.
            details: Additional details from REST API, may be None.

        Returns:
            An IssueNode object.
        """
        try:
            # Validate issue_data
            if not issue_data or not isinstance(issue_data, dict):
                logger.error(f"Invalid issue data: {issue_data}")
                raise ValueError("Invalid issue data format")

            # Extract basic issue information with safety checks
            issue_id = issue_data.get("id")
            if not issue_id:
                logger.error(f"Issue data missing ID: {issue_data}")
                raise ValueError("Issue data missing ID")

            issue_number = issue_data.get("number")
            title = issue_data.get("title", "Untitled Issue")
            body = issue_data.get("body") or ""
            state = issue_data.get("state", "unknown")
            url = issue_data.get("url", "")

            # Parse timestamps with error handling
            created_at = None
            updated_at = None

            if issue_data.get("createdAt"):
                try:
                    created_at = datetime.fromisoformat(issue_data["createdAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing createdAt for issue #{issue_number}: {e}")
                    created_at = datetime.now()  # Fallback to current time

            if issue_data.get("updatedAt"):
                try:
                    updated_at = datetime.fromisoformat(issue_data["updatedAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing updatedAt for issue #{issue_number}: {e}")
                    updated_at = datetime.now()  # Fallback to current time

            if not created_at:
                created_at = datetime.now()  # Fallback if no created_at timestamp

            if not updated_at:
                updated_at = created_at  # Fallback if no updated_at timestamp

            # Extract author information safely
            author = issue_data.get("author", {})
            author_login = author.get("login") if author and isinstance(author, dict) else None

            # Extract closed_at information safely
            closed_at = None
            if issue_data.get("closedAt"):
                try:
                    closed_at = datetime.fromisoformat(issue_data["closedAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing closedAt for issue #{issue_number}: {e}")

            # Extract labels safely
            labels = []
            labels_data = issue_data.get("labels", {})
            if labels_data and isinstance(labels_data, dict) and labels_data.get("nodes"):
                nodes = labels_data.get("nodes", [])
                if isinstance(nodes, list):
                    for label in nodes:
                        if label and isinstance(label, dict) and "name" in label:
                            labels.append(label["name"])

            # Create extra data
            extra = {
                "author": author_login,
                "created_at": created_at.isoformat(),
                "updated_at": updated_at.isoformat(),
            }

            # Safely add details data
            if details is not None and isinstance(details, dict):
                # Add comment information
                if "comments" in details and isinstance(details["comments"], list):
                    extra["comments"] = []
                    for comment in details["comments"]:
                        if comment and isinstance(comment, dict):
                            user = comment.get("user", {})
                            extra["comments"].append({
                                "author": user.get("login") if user and isinstance(user, dict) else None,
                                "body": comment.get("body"),
                                "created_at": comment.get("created_at"),
                            })

                # Add events information
                if "events" in details and isinstance(details["events"], list):
                    extra["events"] = []
                    for event in details["events"]:
                        if event and isinstance(event, dict):
                            actor = event.get("actor", {})
                            label = event.get("label", {})
                            assignee = event.get("assignee", {})

                            event_data = {
                                "event": event.get("event"),
                                "actor": actor.get("login") if actor and isinstance(actor, dict) else None,
                                "created_at": event.get("created_at"),
                                "label": label.get("name") if label and isinstance(label, dict) else None,
                                "assignee": assignee.get("login") if assignee and isinstance(assignee, dict) else None,
                            }
                            extra["events"].append(event_data)

                # Add timeline information
                if "timeline" in details and isinstance(details["timeline"], list):
                    extra["timeline"] = []
                    for item in details["timeline"]:
                        if item and isinstance(item, dict):
                            try:
                                timeline_item = {
                                    "event": item.get("event"),
                                    "actor": None,
                                    "created_at": item.get("created_at"),
                                }

                                # Add actor if available
                                actor = item.get("actor", {})
                                if actor and isinstance(actor, dict):
                                    timeline_item["actor"] = actor.get("login")

                                # Add event-specific fields
                                event_type = item.get("event")

                                if event_type in ["labeled", "unlabeled"]:
                                    label = item.get("label", {})
                                    if label and isinstance(label, dict):
                                        timeline_item["label"] = label.get("name")

                                elif event_type in ["assigned", "unassigned"]:
                                    assignee = item.get("assignee", {})
                                    if assignee and isinstance(assignee, dict):
                                        timeline_item["assignee"] = assignee.get("login")

                                elif event_type in ["milestoned", "demilestoned"]:
                                    milestone = item.get("milestone", {})
                                    if milestone and isinstance(milestone, dict):
                                        timeline_item["milestone"] = milestone.get("title")

                                elif event_type == "renamed":
                                    rename = item.get("rename", {})
                                    if rename and isinstance(rename, dict):
                                        timeline_item["rename"] = {
                                            "from": rename.get("from"),
                                            "to": rename.get("to"),
                                        }

                                elif event_type == "cross-referenced":
                                    source = item.get("source", {})
                                    if source and isinstance(source, dict):
                                        issue = source.get("issue", {})
                                        if issue and isinstance(issue, dict):
                                            timeline_item["cross_reference"] = {
                                                "source": issue.get("number"),
                                                "type": "pr" if issue.get("pull_request") else "issue",
                                            }

                                extra["timeline"].append(timeline_item)
                            except Exception as e:
                                logger.warning(f"Error processing timeline item for issue #{issue_number}: {e}")
                                # Continue with next timeline item

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
        except Exception as e:
            logger.error(f"Error creating issue node for issue #{issue_data.get('number', 'unknown')}: {e}")
            # Create a minimal issue node with the available data
            try:
                issue_id = issue_data.get("id") if issue_data and isinstance(issue_data, dict) else f"issue:unknown-{datetime.now().timestamp()}"
                issue_number = issue_data.get("number") if issue_data and isinstance(issue_data, dict) else 0
                return IssueNode(
                    id=issue_id,
                    title="Error Processing Issue",
                    body=f"Error: {str(e)}",
                    ts=datetime.now(),
                    number=issue_number,
                    state="unknown",
                    url="",
                    extra={"error": str(e)},
                )
            except Exception as inner_e:
                logger.error(f"Critical error creating fallback issue node: {inner_e}")
                # Last resort fallback
                return IssueNode(
                    id=f"issue:error-{datetime.now().timestamp()}",
                    title="Error Processing Issue",
                    body="Critical error occurred",
                    ts=datetime.now(),
                    number=0,
                    state="error",
                    url="",
                    extra={"critical_error": True},
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

        # Return empty list if text is None or empty
        if not text:
            return []

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
        # We already handle None/empty text in extract_mentions, so we can call it directly
        edges = []
        mentions = self.extract_mentions(text)

        # Create a mapping of issue/PR numbers to IDs with safety checks
        issue_map = {}
        pr_map = {}

        for issue in repo_issues:
            if issue and isinstance(issue, dict) and 'number' in issue and 'id' in issue:
                issue_map[f"#{issue['number']}"] = issue["id"]

        for pr in repo_prs:
            if pr and isinstance(pr, dict) and 'number' in pr and 'id' in pr:
                pr_map[f"#{pr['number']}"] = pr["id"]

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
    ) -> Optional[Dict[str, Any]]:
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
    ) -> Optional[Dict[str, Any]]:
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

                    # If we couldn't get details, create a minimal details object
                    if details is None:
                        details = {"files": [], "reviews": [], "comments": [], "commits": [], "review_comments": []}

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
