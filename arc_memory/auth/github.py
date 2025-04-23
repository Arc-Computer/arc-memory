"""GitHub authentication for Arc Memory."""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import jwt
import keyring
import requests
from pydantic import BaseModel

from arc_memory.errors import GitHubAuthError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Constants
KEYRING_SERVICE = "arc-memory"
KEYRING_USERNAME = "github-token"
GITHUB_API_URL = "https://api.github.com"
DEVICE_CODE_URL = f"{GITHUB_API_URL}/login/device/code"
DEVICE_TOKEN_URL = f"{GITHUB_API_URL}/login/oauth/access_token"
USER_AGENT = "Arc-Memory/0.1.0"


class GitHubAppConfig(BaseModel):
    """Configuration for a GitHub App."""

    app_id: str
    private_key: str
    client_id: str
    client_secret: str


def get_token_from_env() -> Optional[str]:
    """Get a GitHub token from environment variables.

    Returns:
        The token, or None if not found.
    """
    # Check for GitHub token in environment variables
    for var in ["GITHUB_TOKEN", "GH_TOKEN"]:
        token = os.environ.get(var)
        if token:
            logger.info(f"Found GitHub token in environment variable {var}")
            return token

    # Check for Codespaces token
    if os.environ.get("CODESPACES") == "true":
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            logger.info("Found GitHub token in Codespaces environment")
            return token

    return None


def get_token_from_keyring() -> Optional[str]:
    """Get a GitHub token from the system keyring.

    Returns:
        The token, or None if not found.
    """
    try:
        token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if token:
            logger.info("Found GitHub token in system keyring")
            return token
    except Exception as e:
        logger.warning(f"Failed to get token from keyring: {e}")

    return None


def store_token_in_keyring(token: str) -> bool:
    """Store a GitHub token in the system keyring.

    Args:
        token: The token to store.

    Returns:
        True if successful, False otherwise.
    """
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
        logger.info("Stored GitHub token in system keyring")
        return True
    except Exception as e:
        logger.warning(f"Failed to store token in keyring: {e}")
        return False


def get_github_token(token: Optional[str] = None) -> str:
    """Get a GitHub token from various sources.

    Args:
        token: An explicit token to use. If None, tries to find a token from other sources.

    Returns:
        A GitHub token.

    Raises:
        GitHubAuthError: If no token could be found.
    """
    # Check explicit token
    if token:
        logger.info("Using explicitly provided GitHub token")
        return token

    # Check environment variables
    env_token = get_token_from_env()
    if env_token:
        return env_token

    # Check keyring
    keyring_token = get_token_from_keyring()
    if keyring_token:
        return keyring_token

    # No token found
    raise GitHubAuthError(
        "No GitHub token found. Please run 'arc auth gh' to authenticate."
    )


def start_device_flow(client_id: str) -> Tuple[str, str, int]:
    """Start the GitHub device flow authentication.

    Args:
        client_id: The GitHub OAuth client ID.

    Returns:
        A tuple of (device_code, verification_uri, interval).

    Raises:
        GitHubAuthError: If the device flow could not be started.
    """
    try:
        response = requests.post(
            DEVICE_CODE_URL,
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            json={
                "client_id": client_id,
                "scope": "repo",
            },
        )
        response.raise_for_status()
        data = response.json()

        device_code = data["device_code"]
        user_code = data["user_code"]
        verification_uri = data["verification_uri"]
        interval = data["interval"]

        logger.info(f"Started device flow. User code: {user_code}")
        print(f"Please visit {verification_uri} and enter code: {user_code}")

        return device_code, verification_uri, interval
    except Exception as e:
        logger.error(f"Failed to start device flow: {e}")
        raise GitHubAuthError(f"Failed to start device flow: {e}")


def poll_device_flow(
    client_id: str, client_secret: str, device_code: str, interval: int, timeout: int = 300
) -> str:
    """Poll the GitHub device flow for an access token.

    Args:
        client_id: The GitHub OAuth client ID.
        client_secret: The GitHub OAuth client secret.
        device_code: The device code from start_device_flow.
        interval: The polling interval in seconds.
        timeout: The timeout in seconds.

    Returns:
        The access token.

    Raises:
        GitHubAuthError: If the device flow timed out or failed.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.post(
                DEVICE_TOKEN_URL,
                headers={
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                if data["error"] == "authorization_pending":
                    # User hasn't authorized yet, wait and try again
                    time.sleep(interval)
                    continue
                else:
                    # Some other error
                    raise GitHubAuthError(f"Device flow error: {data['error']}")

            # Success!
            access_token = data["access_token"]
            logger.info("Successfully obtained access token")
            return access_token
        except GitHubAuthError:
            # Re-raise GitHubAuthError
            raise
        except Exception as e:
            logger.error(f"Failed to poll device flow: {e}")
            raise GitHubAuthError(f"Failed to poll device flow: {e}")

        time.sleep(interval)

    # Timeout
    raise GitHubAuthError("Device flow timed out. Please try again.")


def create_jwt(app_id: str, private_key: str, expiration: int = 600) -> str:
    """Create a JWT for GitHub App authentication.

    Args:
        app_id: The GitHub App ID.
        private_key: The GitHub App private key.
        expiration: The expiration time in seconds.

    Returns:
        A JWT for GitHub App authentication.
    """
    now = int(time.time())
    payload = {
        "iat": now,  # Issued at time
        "exp": now + expiration,  # Expiration time
        "iss": app_id,  # Issuer (GitHub App ID)
    }

    try:
        token = jwt.encode(payload, private_key, algorithm="RS256")
        return token
    except Exception as e:
        logger.error(f"Failed to create JWT: {e}")
        raise GitHubAuthError(f"Failed to create JWT: {e}")


def get_installation_token(
    app_id: str, private_key: str, installation_id: str
) -> Tuple[str, datetime]:
    """Get an installation token for a GitHub App.

    Args:
        app_id: The GitHub App ID.
        private_key: The GitHub App private key.
        installation_id: The installation ID.

    Returns:
        A tuple of (token, expiration).

    Raises:
        GitHubAuthError: If the installation token could not be obtained.
    """
    try:
        # Create JWT
        jwt_token = create_jwt(app_id, private_key)

        # Get installation token
        response = requests.post(
            f"{GITHUB_API_URL}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": USER_AGENT,
            },
        )
        response.raise_for_status()
        data = response.json()

        token = data["token"]
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))

        logger.info(f"Got installation token, expires at {expires_at}")
        return token, expires_at
    except Exception as e:
        logger.error(f"Failed to get installation token: {e}")
        raise GitHubAuthError(f"Failed to get installation token: {e}")


def get_installation_id(app_id: str, private_key: str, owner: str, repo: str) -> str:
    """Get the installation ID for a GitHub App in a repository.

    Args:
        app_id: The GitHub App ID.
        private_key: The GitHub App private key.
        owner: The repository owner.
        repo: The repository name.

    Returns:
        The installation ID.

    Raises:
        GitHubAuthError: If the installation ID could not be obtained.
    """
    try:
        # Create JWT
        jwt_token = create_jwt(app_id, private_key)

        # Get installation
        response = requests.get(
            f"{GITHUB_API_URL}/repos/{owner}/{repo}/installation",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": USER_AGENT,
            },
        )
        response.raise_for_status()
        data = response.json()

        installation_id = data["id"]
        logger.info(f"Got installation ID: {installation_id}")
        return str(installation_id)
    except Exception as e:
        logger.error(f"Failed to get installation ID: {e}")
        raise GitHubAuthError(
            f"Failed to get installation ID for {owner}/{repo}: {e}. "
            "Make sure the Arc Memory GitHub App is installed in this repository."
        )
