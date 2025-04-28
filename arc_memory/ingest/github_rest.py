"""GitHub REST API client for Arc Memory."""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from arc_memory.errors import GitHubAuthError, IngestError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Constants
GITHUB_API_URL = "https://api.github.com"
USER_AGENT = "Arc-Memory/0.2.2"

# Rate limit constants
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_BACKOFF = 2  # Exponential backoff factor
DEFAULT_RETRY_DELAY = 1  # Initial delay in seconds
RATE_LIMIT_BUFFER = 100  # Buffer to avoid hitting rate limit


class GitHubRESTClient:
    """REST client for GitHub API with rate limit handling and backoff strategies."""

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
        # Rate limit tracking
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        self.rate_limit_limit = None

        # Initialize rate limit info
        self._update_rate_limit_info()

    def _update_rate_limit_info(self) -> None:
        """Update rate limit information from the GitHub API."""
        try:
            url = f"{GITHUB_API_URL}/rate_limit"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                core_limits = data.get("resources", {}).get("core", {})

                self.rate_limit_limit = core_limits.get("limit")
                self.rate_limit_remaining = core_limits.get("remaining")
                reset_timestamp = core_limits.get("reset")

                if reset_timestamp:
                    self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)

                logger.debug(
                    f"Rate limit: {self.rate_limit_remaining}/{self.rate_limit_limit} "
                    f"remaining, resets at {self.rate_limit_reset}"
                )
            else:
                logger.warning(f"Failed to get rate limit info: {response.status_code}")
        except Exception as e:
            logger.warning(f"Error updating rate limit info: {e}")

    def _should_wait_for_rate_limit(self) -> Tuple[bool, float]:
        """Check if we should wait for rate limit to reset.

        Returns:
            A tuple of (should_wait, wait_seconds)
        """
        if self.rate_limit_remaining is None or self.rate_limit_reset is None:
            return False, 0

        # If we're close to the rate limit, wait
        if self.rate_limit_remaining < RATE_LIMIT_BUFFER:
            now = datetime.now()
            if self.rate_limit_reset > now:
                wait_seconds = (self.rate_limit_reset - now).total_seconds() + 1  # Add 1 second buffer
                return True, wait_seconds

        return False, 0

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = DEFAULT_RETRY_COUNT,
    ) -> Dict[str, Any]:
        """Make a request to the GitHub API with retry and rate limit handling.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint (e.g., "/repos/{owner}/{repo}/pulls").
            params: Query parameters.
            data: Form data.
            json_data: JSON data.
            retry_count: Number of retries for transient errors.

        Returns:
            The response data.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        url = f"{GITHUB_API_URL}{endpoint}"

        # Check if we should wait for rate limit to reset
        should_wait, wait_seconds = self._should_wait_for_rate_limit()
        if should_wait:
            logger.warning(f"Rate limit low ({self.rate_limit_remaining}), waiting {wait_seconds:.1f} seconds")
            time.sleep(wait_seconds)
            # Update rate limit info after waiting
            self._update_rate_limit_info()

        # Initialize retry variables
        attempts = 0
        delay = DEFAULT_RETRY_DELAY

        while attempts <= retry_count:
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    data=data,
                    json=json_data,
                    timeout=30,  # Add a reasonable timeout
                )

                # Update rate limit info from headers
                if "X-RateLimit-Remaining" in response.headers:
                    self.rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
                if "X-RateLimit-Reset" in response.headers:
                    self.rate_limit_reset = datetime.fromtimestamp(int(response.headers["X-RateLimit-Reset"]))
                if "X-RateLimit-Limit" in response.headers:
                    self.rate_limit_limit = int(response.headers["X-RateLimit-Limit"])

                # Log rate limit info
                if self.rate_limit_remaining is not None and self.rate_limit_reset is not None:
                    logger.debug(
                        f"Rate limit: {self.rate_limit_remaining}/{self.rate_limit_limit} "
                        f"remaining, resets at {self.rate_limit_reset}"
                    )

                # Handle rate limit exceeded
                if response.status_code == 403 and "rate limit" in response.text.lower():
                    logger.warning("GitHub rate limit exceeded")

                    # If we have reset info and haven't exceeded retry count, wait until reset
                    if self.rate_limit_reset and attempts < retry_count:
                        now = datetime.now()
                        if self.rate_limit_reset > now:
                            wait_seconds = (self.rate_limit_reset - now).total_seconds() + 1
                            logger.info(f"Waiting {wait_seconds:.1f} seconds for rate limit reset (attempt {attempts+1}/{retry_count})")
                            time.sleep(wait_seconds)
                            # Increment attempts and try again
                            attempts += 1
                            continue

                    # If we can't determine when to retry or have exceeded retry count, raise an error
                    if attempts >= retry_count:
                        raise IngestError(f"GitHub rate limit exceeded after {attempts} retries")
                    else:
                        raise IngestError("GitHub rate limit exceeded and reset time unknown")

                # Handle authentication errors
                if response.status_code == 401:
                    logger.error("GitHub authentication error")
                    raise GitHubAuthError("GitHub authentication error")

                # Handle secondary rate limits (abuse detection)
                if response.status_code == 403 and "abuse" in response.text.lower():
                    if attempts < retry_count:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"GitHub abuse detection triggered, waiting {retry_after} seconds (attempt {attempts+1}/{retry_count})")
                        time.sleep(retry_after)
                        attempts += 1
                        continue
                    else:
                        raise IngestError(f"GitHub abuse detection triggered after {attempts} retries")

                # Handle server errors (5xx) with retry
                if 500 <= response.status_code < 600:
                    if attempts < retry_count:
                        wait_time = delay * (DEFAULT_RETRY_BACKOFF ** attempts)
                        logger.warning(f"GitHub server error ({response.status_code}), retrying in {wait_time} seconds")
                        time.sleep(wait_time)
                        attempts += 1
                        continue

                # Check for other errors
                response.raise_for_status()

                # Return the response data
                return response.json()

            except GitHubAuthError:
                # Re-raise authentication errors immediately
                raise

            except requests.exceptions.RequestException as e:
                # Handle network errors with retry
                if attempts < retry_count:
                    wait_time = delay * (DEFAULT_RETRY_BACKOFF ** attempts)
                    logger.warning(f"GitHub API request error: {e}, retrying in {wait_time} seconds")
                    time.sleep(wait_time)
                    attempts += 1
                    continue

                logger.error(f"GitHub API request error after {attempts} retries: {e}")
                raise IngestError(f"GitHub API request error: {e}")

            except Exception as e:
                logger.exception(f"Unexpected error making GitHub API request: {e}")
                raise IngestError(f"Failed to make GitHub API request: {e}")

            # This line is only reached if we get a successful response
            # The loop will exit after returning the response data

    def paginate(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_pages: int = 100,
        retry_count: int = DEFAULT_RETRY_COUNT,
    ) -> List[Dict[str, Any]]:
        """Make a paginated request to the GitHub API with rate limit handling.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint (e.g., "/repos/{owner}/{repo}/pulls").
            params: Query parameters.
            data: Form data.
            json_data: JSON data.
            max_pages: Maximum number of pages to fetch.
            retry_count: Number of retries for transient errors.

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

            # Make the request with retry logic
            response_data = self.request(method, endpoint, params, data, json_data, retry_count)

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

            # Check rate limit and implement adaptive paging
            if self.rate_limit_remaining is not None:
                # If we're getting low on rate limit, slow down
                if self.rate_limit_remaining < RATE_LIMIT_BUFFER:
                    wait_time = 1.0  # Base wait time in seconds
                    logger.warning(f"Rate limit low ({self.rate_limit_remaining}), slowing down requests")
                    time.sleep(wait_time)

                # If we're very low, wait longer
                if self.rate_limit_remaining < RATE_LIMIT_BUFFER / 2:
                    wait_time = 2.0
                    logger.warning(f"Rate limit very low ({self.rate_limit_remaining}), waiting {wait_time} seconds")
                    time.sleep(wait_time)

        return all_items

    def batch_request(
        self,
        method: str,
        endpoints: List[str],
        batch_size: int = 5,
        delay: float = 0.5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Make multiple requests in batches to avoid rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoints: List of API endpoints to request.
            batch_size: Number of requests to make in each batch.
            delay: Delay between batches in seconds.
            **kwargs: Additional arguments to pass to request().

        Returns:
            A list of response data items, one for each endpoint.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        results = []

        # Process endpoints in batches
        for i in range(0, len(endpoints), batch_size):
            batch = endpoints[i:i + batch_size]
            batch_results = []

            # Process each endpoint in the batch
            for endpoint in batch:
                try:
                    result = self.request(method, endpoint, **kwargs)
                    batch_results.append(result)
                except Exception as e:
                    logger.error(f"Error processing endpoint {endpoint}: {e}")
                    # Add None to maintain order with endpoints
                    batch_results.append(None)

            # Add batch results to overall results
            results.extend(batch_results)

            # Wait between batches if not the last batch
            if i + batch_size < len(endpoints) and delay > 0:
                time.sleep(delay)

            # Check rate limit and wait if necessary
            should_wait, wait_seconds = self._should_wait_for_rate_limit()
            if should_wait:
                logger.warning(f"Rate limit low ({self.rate_limit_remaining}), waiting {wait_seconds:.1f} seconds")
                time.sleep(wait_seconds)
                # Update rate limit info after waiting
                self._update_rate_limit_info()

        return results

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

    def get_commits_for_pr(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get commits for a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            A list of commits for the pull request.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/commits"
        return self.paginate("GET", endpoint)

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

    def get_review_comments(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get review comments for a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            A list of review comments for the pull request.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/comments"
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

    def get_issue_events(self, owner: str, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """Get events for an issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            A list of events for the issue.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/events"
        return self.paginate("GET", endpoint)

    def get_issue_timeline(self, owner: str, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """Get timeline for an issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            A list of timeline events for the issue.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        # This endpoint requires a special Accept header
        original_accept = self.headers["Accept"]
        try:
            self.headers["Accept"] = "application/vnd.github.mockingbird-preview+json"
            endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/timeline"
            return self.paginate("GET", endpoint)
        finally:
            # Restore the original Accept header
            self.headers["Accept"] = original_accept

    def get_pr_details_batch(self, owner: str, repo: str, pr_numbers: List[int]) -> List[Dict[str, Any]]:
        """Get details for multiple pull requests in batches.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_numbers: List of PR numbers.

        Returns:
            A list of PR details, one for each PR number.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        endpoints = [f"/repos/{owner}/{repo}/pulls/{pr_number}" for pr_number in pr_numbers]
        return self.batch_request("GET", endpoints)

    def get_issue_details_batch(self, owner: str, repo: str, issue_numbers: List[int]) -> List[Dict[str, Any]]:
        """Get details for multiple issues in batches.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_numbers: List of issue numbers.

        Returns:
            A list of issue details, one for each issue number.

        Raises:
            GitHubAuthError: If there's an error with GitHub authentication.
            IngestError: If there's an error making the request.
        """
        endpoints = [f"/repos/{owner}/{repo}/issues/{issue_number}" for issue_number in issue_numbers]
        return self.batch_request("GET", endpoints)
