"""GitHub authentication for Arc Memory."""

import json
import os
import time
from datetime import datetime
from typing import Optional, Tuple

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
KEYRING_APP_USERNAME = "github-app"
GITHUB_API_URL = "https://api.github.com"
GITHUB_URL = "https://github.com"
DEVICE_CODE_URL = f"{GITHUB_URL}/login/device/code"
DEVICE_TOKEN_URL = f"{GITHUB_URL}/login/oauth/access_token"
USER_AGENT = "Arc-Memory/0.5.0"

# Environment variable names
ENV_APP_ID = "ARC_GITHUB_APP_ID"
ENV_PRIVATE_KEY_PATH = "ARC_GITHUB_PRIVATE_KEY_PATH"
ENV_PRIVATE_KEY = "ARC_GITHUB_PRIVATE_KEY"
ENV_CLIENT_ID = "ARC_GITHUB_CLIENT_ID"
ENV_CLIENT_SECRET = "ARC_GITHUB_CLIENT_SECRET"


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


def get_github_app_config_from_env() -> Optional[GitHubAppConfig]:
    """Get GitHub App configuration from environment variables.

    Returns:
        The GitHub App configuration, or None if not found.
    """
    app_id = os.environ.get(ENV_APP_ID)
    client_id = os.environ.get(ENV_CLIENT_ID)
    client_secret = os.environ.get(ENV_CLIENT_SECRET)

    # Check for private key
    private_key = os.environ.get(ENV_PRIVATE_KEY)
    if not private_key and os.environ.get(ENV_PRIVATE_KEY_PATH):
        try:
            with open(os.environ.get(ENV_PRIVATE_KEY_PATH), "r") as f:
                private_key = f.read()
        except Exception as e:
            logger.warning(f"Failed to read private key file: {e}")

    # Ensure we have all required values
    if not all([app_id, private_key, client_id, client_secret]):
        return None

    logger.info(f"Found GitHub App configuration in environment variables (App ID: {app_id})")
    return GitHubAppConfig(
        app_id=app_id,
        private_key=private_key,
        client_id=client_id,
        client_secret=client_secret
    )


def get_github_app_config_from_keyring() -> Optional[GitHubAppConfig]:
    """Get GitHub App configuration from the system keyring.

    Returns:
        The GitHub App configuration, or None if not found.
    """
    try:
        config_json = keyring.get_password(KEYRING_SERVICE, KEYRING_APP_USERNAME)
        if config_json:
            config_dict = json.loads(config_json)
            logger.info(f"Found GitHub App configuration in system keyring (App ID: {config_dict.get('app_id')})")
            return GitHubAppConfig(**config_dict)
    except Exception as e:
        logger.warning(f"Failed to get GitHub App configuration from keyring: {e}")

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


def store_github_app_config_in_keyring(config: GitHubAppConfig) -> bool:
    """Store GitHub App configuration in the system keyring.

    Args:
        config: The GitHub App configuration to store.

    Returns:
        True if successful, False otherwise.
    """
    try:
        config_json = json.dumps(config.model_dump())
        keyring.set_password(KEYRING_SERVICE, KEYRING_APP_USERNAME, config_json)
        logger.info(f"Stored GitHub App configuration in system keyring (App ID: {config.app_id})")
        return True
    except Exception as e:
        logger.warning(f"Failed to store GitHub App configuration in keyring: {e}")
        return False


def get_github_app_config() -> Optional[GitHubAppConfig]:
    """Get GitHub App configuration from various sources.

    Returns:
        The GitHub App configuration, or None if not found.
    """
    # Check environment variables
    env_config = get_github_app_config_from_env()
    if env_config:
        return env_config

    # Check keyring
    keyring_config = get_github_app_config_from_keyring()
    if keyring_config:
        return keyring_config

    return None


def get_installation_token_for_repo(
    owner: str, repo: str, app_config: Optional[GitHubAppConfig] = None
) -> Optional[str]:
    """Get an installation token for a repository.

    Args:
        owner: The repository owner.
        repo: The repository name.
        app_config: The GitHub App configuration. If None, tries to find it from other sources.

    Returns:
        The installation token, or None if it could not be obtained.
    """
    if not app_config:
        app_config = get_github_app_config()
        if not app_config:
            logger.warning("No GitHub App configuration found")
            return None

    try:
        installation_id = get_installation_id(app_config.app_id, app_config.private_key, owner, repo)
        token, _ = get_installation_token(app_config.app_id, app_config.private_key, installation_id)
        logger.info(f"Got installation token for {owner}/{repo}")
        return token
    except GitHubAuthError as e:
        logger.warning(f"Failed to get installation token: {e}")
        return None


def get_github_token(token: Optional[str] = None, owner: Optional[str] = None, repo: Optional[str] = None, allow_failure: bool = False) -> Optional[str]:
    """Get a GitHub token from various sources.

    Args:
        token: An explicit token to use. If None, tries to find a token from other sources.
        owner: The repository owner. Used for GitHub App installation tokens.
        repo: The repository name. Used for GitHub App installation tokens.
        allow_failure: If True, returns None instead of raising an error when no token is found.

    Returns:
        A GitHub token, or None if allow_failure is True and no token could be found.

    Raises:
        GitHubAuthError: If no token could be found and allow_failure is False.
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

    # Check GitHub App installation token if owner and repo are provided
    if owner and repo:
        installation_token = get_installation_token_for_repo(owner, repo)
        if installation_token:
            return installation_token

    # No token found
    if allow_failure:
        logger.warning("No GitHub token found. GitHub data will not be included in the graph.")
        return None
    else:
        raise GitHubAuthError(
            "No GitHub token found. Please run 'arc auth gh' to authenticate with GitHub. "
            "Without GitHub authentication, only Git data will be included in the graph."
        )



def validate_client_id(client_id: str) -> bool:
    """Validate that a GitHub OAuth client ID is properly formatted.

    Args:
        client_id: The client ID to validate.

    Returns:
        True if the client ID is valid, False otherwise.
    """
    # GitHub client IDs are typically 20 characters
    if not client_id:
        return False

    # Note: This validation is intentionally strict to catch potential errors
    # Most GitHub client IDs are 20 characters long
    # Some newer ones start with "Iv1." and are longer
    if client_id.startswith("Iv1."):
        return len(client_id) >= 15
    else:
        return len(client_id) >= 18



def start_device_flow(client_id: str) -> Tuple[str, str, int]:
    """Start the GitHub device flow authentication.

    Args:
        client_id: The GitHub OAuth client ID.

    Returns:
        A tuple of (device_code, verification_uri, interval).

    Raises:
        GitHubAuthError: If the device flow could not be started.
    """
    # Validate the client ID
    if not validate_client_id(client_id):
        logger.error(f"Invalid GitHub OAuth client ID: {client_id}")
        raise GitHubAuthError(
            f"Invalid GitHub OAuth client ID: {client_id}. "
            "Please provide a valid client ID or check your configuration."
        )

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

        # Check for specific error responses
        if response.status_code == 400:
            try:
                error_data = response.json()
                error_message = error_data.get("error_description", "Unknown error")
                logger.error(f"GitHub API error: {error_message}")
                raise GitHubAuthError(
                    f"GitHub authentication failed: {error_message}. "
                    "This may be due to an invalid client ID or rate limiting."
                )
            except (ValueError, KeyError):
                pass  # Fall back to generic error handling

        response.raise_for_status()
        data = response.json()

        device_code = data["device_code"]
        user_code = data["user_code"]
        verification_uri = data["verification_uri"]
        interval = data["interval"]

        logger.info(f"Started device flow. User code: {user_code}")
        print(f"Please visit {verification_uri} and enter code: {user_code}")

        return device_code, verification_uri, interval
    except GitHubAuthError:
        # Re-raise GitHubAuthError
        raise
    except Exception as e:
        logger.error(f"Failed to start device flow: {e}")
        raise GitHubAuthError(
            f"Failed to start device flow: {e}. "
            "Please check your internet connection and try again."
        )


def poll_device_flow(
    client_id: str, device_code: str, interval: int, timeout: int = 300
) -> str:
    """Poll the GitHub device flow for an access token.

    Args:
        client_id: The GitHub OAuth client ID.
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
