"""Linear authentication for Arc Memory."""

import json
import os
import secrets
import time
from datetime import datetime
from typing import List, Optional, Tuple, Union

import keyring
import requests
from pydantic import BaseModel, Field

from arc_memory.errors import LinearAuthError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Constants
KEYRING_SERVICE = "arc-memory"
KEYRING_USERNAME = "linear-token"
KEYRING_OAUTH_USERNAME = "linear-oauth-token"
LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_URL = "https://linear.app"
DEVICE_CODE_URL = f"{LINEAR_URL}/oauth/device/code"
DEVICE_TOKEN_URL = f"{LINEAR_URL}/oauth/token"
OAUTH_AUTHORIZE_URL = f"{LINEAR_URL}/oauth/authorize"
OAUTH_TOKEN_URL = f"{LINEAR_URL}/oauth/token"
OAUTH_REVOKE_URL = f"{LINEAR_URL}/oauth/revoke"
USER_AGENT = "Arc-Memory/0.2.2"

# Default redirect URI for local development
DEFAULT_REDIRECT_URI = "http://localhost:8000/oauth/callback"

# Environment variable names
ENV_CLIENT_ID = "ARC_LINEAR_CLIENT_ID"
ENV_CLIENT_SECRET = "ARC_LINEAR_CLIENT_SECRET"
ENV_REDIRECT_URI = "ARC_LINEAR_REDIRECT_URI"


class LinearOAuthToken(BaseModel):
    """OAuth token for Linear API."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 315705599  # Default to a very long expiration (10 years)
    scope: Union[str, List[str]] = "read"  # Can be string or list based on Linear's docs
    created_at: datetime = Field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """Check if the token is expired.

        Returns:
            True if the token is expired, False otherwise.
        """
        # Calculate expiration time
        expiration_time = self.created_at.timestamp() + self.expires_in
        current_time = datetime.now().timestamp()
        return current_time >= expiration_time


class LinearAppConfig(BaseModel):
    """Configuration for a Linear App."""

    client_id: str
    client_secret: str
    redirect_uri: str = DEFAULT_REDIRECT_URI
    scopes: List[str] = ["read", "write", "issues:create", "comments:create"]


def get_token_from_env() -> Optional[str]:
    """Get a Linear token from environment variables.

    Returns:
        The token, or None if not found.
    """
    # Check for Linear token in environment variables
    for var in ["LINEAR_API_KEY", "LINEAR_TOKEN"]:
        token = os.environ.get(var)
        if token:
            logger.info(f"Found Linear token in environment variable {var}")
            return token

    return None


def get_token_from_keyring() -> Optional[str]:
    """Get a Linear token from the system keyring.

    Returns:
        The token, or None if not found.
    """
    try:
        token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if token:
            logger.info("Found Linear token in system keyring")
            return token
    except Exception as e:
        logger.warning(f"Failed to get token from keyring: {e}")

    return None


def get_oauth_token_from_keyring() -> Optional[LinearOAuthToken]:
    """Get a Linear OAuth token from the system keyring.

    Returns:
        The OAuth token, or None if not found.
    """
    try:
        token_json = keyring.get_password(KEYRING_SERVICE, KEYRING_OAUTH_USERNAME)
        if token_json:
            token_dict = json.loads(token_json)
            logger.info("Found Linear OAuth token in system keyring")
            return LinearOAuthToken(**token_dict)
    except Exception as e:
        logger.warning(f"Failed to get OAuth token from keyring: {e}")

    return None


def get_linear_app_config_from_env() -> Optional[LinearAppConfig]:
    """Get Linear App configuration from environment variables.

    Returns:
        The Linear App configuration, or None if not found.
    """
    client_id = os.environ.get(ENV_CLIENT_ID)
    client_secret = os.environ.get(ENV_CLIENT_SECRET)
    redirect_uri = os.environ.get(ENV_REDIRECT_URI, DEFAULT_REDIRECT_URI)

    # Ensure we have all required values
    if not all([client_id, client_secret]):
        return None

    logger.info(f"Found Linear App configuration in environment variables (Client ID: {client_id})")
    return LinearAppConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )


def store_token_in_keyring(token: str) -> bool:
    """Store a Linear token in the system keyring.

    Args:
        token: The token to store.

    Returns:
        True if successful, False otherwise.
    """
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
        logger.info("Stored Linear token in system keyring")
        return True
    except Exception as e:
        logger.warning(f"Failed to store token in keyring: {e}")
        return False


def store_oauth_token_in_keyring(token: LinearOAuthToken) -> bool:
    """Store a Linear OAuth token in the system keyring.

    Args:
        token: The OAuth token to store.

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Convert to JSON for storage
        token_dict = token.model_dump()
        # Convert datetime to string for JSON serialization
        token_dict["created_at"] = token_dict["created_at"].isoformat()
        token_json = json.dumps(token_dict)

        keyring.set_password(KEYRING_SERVICE, KEYRING_OAUTH_USERNAME, token_json)
        logger.info("Stored Linear OAuth token in system keyring")
        return True
    except Exception as e:
        logger.warning(f"Failed to store OAuth token in keyring: {e}")
        return False


def get_linear_token(token: Optional[str] = None, allow_failure: bool = False, prefer_oauth: bool = True) -> Optional[str]:
    """Get a Linear token from various sources.

    Args:
        token: An explicit token to use. If None, tries to find a token from other sources.
        allow_failure: If True, returns None instead of raising an error when no token is found.
        prefer_oauth: If True, tries to get an OAuth token first before falling back to API key.

    Returns:
        A Linear token, or None if allow_failure is True and no token could be found.

    Raises:
        LinearAuthError: If no token could be found and allow_failure is False.
    """
    # Check explicit token
    if token:
        logger.info("Using explicitly provided Linear token")
        return token

    # Check for OAuth token if preferred
    if prefer_oauth:
        oauth_token = get_oauth_token_from_keyring()
        if oauth_token:
            if oauth_token.is_expired():
                logger.warning("OAuth token is expired. Falling back to other authentication methods.")
            else:
                logger.info("Using OAuth token from keyring")
                return oauth_token.access_token

    # Check environment variables
    env_token = get_token_from_env()
    if env_token:
        return env_token

    # Check keyring for API key
    keyring_token = get_token_from_keyring()
    if keyring_token:
        return keyring_token

    # No token found
    if allow_failure:
        logger.warning("No Linear token found. Linear data will not be included in the graph.")
        return None
    else:
        raise LinearAuthError(
            "No Linear token found. Please run 'arc auth linear' to authenticate with Linear. "
            "Without Linear authentication, Linear data will not be included in the graph."
        )


def validate_client_id(client_id: str) -> bool:
    """Validate that a Linear OAuth client ID is properly formatted.

    Args:
        client_id: The client ID to validate.

    Returns:
        True if the client ID is valid, False otherwise.
    """
    # Linear client IDs are typically alphanumeric strings
    if not client_id:
        return False

    # Basic validation - Linear client IDs are typically at least 10 characters
    return len(client_id) >= 10


def start_device_flow(client_id: str) -> Tuple[str, str, str, int]:
    """Start the Linear device flow authentication.

    Args:
        client_id: The Linear OAuth client ID.

    Returns:
        A tuple of (device_code, user_code, verification_uri, interval).

    Raises:
        LinearAuthError: If the device flow could not be started.
    """
    # Validate the client ID
    if not validate_client_id(client_id):
        logger.error(f"Invalid Linear OAuth client ID: {client_id}")
        raise LinearAuthError(
            f"Invalid Linear OAuth client ID: {client_id}. "
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
                "scope": "read,issues:read,issues:write",
            },
        )

        # Check for specific error responses
        if response.status_code == 400:
            try:
                error_data = response.json()
                error_message = error_data.get("error_description", "Unknown error")
                logger.error(f"Linear API error: {error_message}")
                raise LinearAuthError(
                    f"Linear authentication failed: {error_message}. "
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
        logger.info(f"Please visit {verification_uri} and enter code: {user_code}")

        return device_code, user_code, verification_uri, interval
    except LinearAuthError:
        # Re-raise LinearAuthError
        raise
    except Exception as e:
        logger.error(f"Failed to start device flow: {e}")
        raise LinearAuthError(
            f"Failed to start device flow: {e}. "
            "Please check your internet connection and try again."
        )


def poll_device_flow(
    client_id: str, client_secret: str, device_code: str, interval: int, timeout: int = 300
) -> str:
    """Poll the Linear device flow for an access token.

    Args:
        client_id: The Linear OAuth client ID.
        client_secret: The Linear OAuth client secret.
        device_code: The device code from start_device_flow.
        interval: The polling interval in seconds.
        timeout: The timeout in seconds.

    Returns:
        The access token.

    Raises:
        LinearAuthError: If the device flow timed out or failed.
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
                    raise LinearAuthError(f"Device flow error: {data['error']}")

            # Success!
            access_token = data["access_token"]
            logger.info("Successfully obtained access token")
            return access_token
        except LinearAuthError:
            # Re-raise LinearAuthError
            raise
        except Exception as e:
            logger.error(f"Failed to poll device flow: {e}")
            raise LinearAuthError(f"Failed to poll device flow: {e}")

    # Timeout
    raise LinearAuthError("Device flow timed out. Please try again.")


def generate_oauth_url(config: LinearAppConfig, state: Optional[str] = None) -> str:
    """Generate the OAuth authorization URL.

    Args:
        config: The Linear App configuration.
        state: Optional state parameter for CSRF protection.

    Returns:
        The authorization URL.
    """
    # Create scope string from list
    scope = ",".join(config.scopes)

    # Build the URL
    params = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": scope,
    }

    # Add state parameter if provided
    if state:
        params["state"] = state

    # Build the query string
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])

    # Return the full URL
    return f"{OAUTH_AUTHORIZE_URL}?{query_string}"


def exchange_code_for_token(
    config: LinearAppConfig, code: str
) -> LinearOAuthToken:
    """Exchange an authorization code for an access token.

    Args:
        config: The Linear App configuration.
        code: The authorization code from the OAuth callback.

    Returns:
        The OAuth token.

    Raises:
        LinearAuthError: If the token exchange failed.
    """
    try:
        response = requests.post(
            OAUTH_TOKEN_URL,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": USER_AGENT,
            },
            data={
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "code": code,
                "redirect_uri": config.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise LinearAuthError(f"Token exchange error: {data.get('error_description', data['error'])}")

        # Create and return the token
        token = LinearOAuthToken(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 315705599),  # Default to ~10 years if not provided
            scope=data.get("scope", "read"),
            created_at=datetime.now(),
        )

        logger.info("Successfully exchanged code for access token")
        return token
    except LinearAuthError:
        # Re-raise LinearAuthError
        raise
    except Exception as e:
        logger.error(f"Failed to exchange code for token: {e}")
        raise LinearAuthError(f"Failed to exchange code for token: {e}")


def revoke_token(token: str) -> bool:
    """Revoke a Linear access token.

    Args:
        token: The access token to revoke.

    Returns:
        True if successful, False otherwise.
    """
    try:
        response = requests.post(
            OAUTH_REVOKE_URL,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": USER_AGENT,
                "Authorization": f"Bearer {token}",
            },
        )

        # 200 means token was revoked
        if response.status_code == 200:
            logger.info("Successfully revoked access token")
            return True

        # 400 means token was already revoked or invalid
        if response.status_code == 400:
            logger.warning("Token was already revoked or is invalid")
            return True  # Still return True since the token is effectively revoked

        # Other status codes indicate an error
        logger.error(f"Failed to revoke token: {response.status_code} {response.text}")
        return False
    except Exception as e:
        logger.error(f"Failed to revoke token: {e}")
        return False


def generate_secure_state() -> str:
    """Generate a secure random state parameter for CSRF protection.

    Returns:
        A secure random string.
    """
    return secrets.token_urlsafe(32)
