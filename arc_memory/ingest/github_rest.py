"""GitHub REST API client for Arc Memory."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from arc_memory.errors import GitHubAuthError, IngestError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Constants
GITHUB_API_URL = "https://api.github.com"
USER_AGENT = "Arc-Memory/0.2.1"


class GitHubRESTClient:
    """REST client for GitHub API."""

    def __init__(self, token: str):
        """Initialize the REST client.

        Args:
            token: GitHub token to use for API calls.
        """
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": USER_AGENT,
        }
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a request to the GitHub API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint (e.g., "/repos/{owner}/{repo}/pulls").
            params: Query parameters.
            data: Form data.
            json_data: JSON data.

        Returns:
            The response data.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        url = f"{GITHUB_API_URL}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                data=data,
                json=json_data,
            )

            # Check for rate limit info in headers
            if "X-RateLimit-Remaining" in response.headers:
                self.rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
            if "X-RateLimit-Reset" in response.headers:
                self.rate_limit_reset = datetime.fromtimestamp(int(response.headers["X-RateLimit-Reset"]))

            # Log rate limit info
            if self.rate_limit_remaining is not None and self.rate_limit_reset is not None:
                logger.debug(f"Rate limit: {self.rate_limit_remaining} remaining, resets at {self.rate_limit_reset}")

            # Check for rate limit exceeded
            if response.status_code == 403 and "rate limit" in response.text.lower():
                logger.error("GitHub rate limit exceeded")

                # In a real implementation, we would wait until the rate limit resets
                # But for testing purposes, we'll just raise an error
                raise IngestError("GitHub rate limit exceeded")

            # Check for authentication errors
            if response.status_code == 401:
                logger.error("GitHub authentication error")
                raise GitHubAuthError("GitHub authentication error")

            # Check for other errors
            response.raise_for_status()

            # Return the response data
            return response.json()
        except GitHubAuthError:
            # Re-raise GitHubAuthError
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request error: {e}")
            raise IngestError(f"GitHub API request error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error making GitHub API request: {e}")
            raise IngestError(f"Failed to make GitHub API request: {e}")

    def paginate(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_pages: int = 100,
    ) -> List[Dict[str, Any]]:
        """Make a paginated request to the GitHub API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint (e.g., "/repos/{owner}/{repo}/pulls").
            params: Query parameters.
            data: Form data.
            json_data: JSON data.
            max_pages: Maximum number of pages to fetch.

        Returns:
            A list of response data items.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        all_items = []
        page = 1
        per_page = 100

        # Initialize params if None
        if params is None:
            params = {}

        # Set per_page parameter
        params["per_page"] = per_page

        while page <= max_pages:
            # Set page parameter
            params["page"] = page

            # Make the request
            response_data = self.request(method, endpoint, params, data, json_data)

            # Check if response is a list
            if not isinstance(response_data, list):
                logger.warning(f"Expected list response, got {type(response_data)}")
                break

            # Add items to the result
            all_items.extend(response_data)

            # Check if we've reached the end
            if len(response_data) < per_page:
                break

            # Increment page
            page += 1

            # Check rate limit and log a warning if necessary
            if self.rate_limit_remaining is not None and self.rate_limit_remaining < 100:
                logger.warning(f"Rate limit low ({self.rate_limit_remaining}), consider slowing down requests")

        return all_items

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get the files changed in a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            A list of files changed in the pull request.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
        return self.paginate("GET", endpoint)

    def get_commit_details(self, owner: str, repo: str, commit_sha: str) -> Dict[str, Any]:
        """Get details of a commit.

        Args:
            owner: Repository owner.
            repo: Repository name.
            commit_sha: Commit SHA.

        Returns:
            Commit details.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        endpoint = f"/repos/{owner}/{repo}/commits/{commit_sha}"
        return self.request("GET", endpoint)

    def get_pr_reviews(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get reviews for a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            A list of reviews for the pull request.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        return self.paginate("GET", endpoint)

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """Get comments for an issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            A list of comments for the issue.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        return self.paginate("GET", endpoint)

    def get_pr_comments(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get comments for a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            A list of comments for the pull request.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        # PR comments are actually issue comments in GitHub's API
        return self.get_issue_comments(owner, repo, pr_number)
