"""Linear authentication for Arc Memory."""

import json
import os
import time
from datetime import datetime
from typing import Optional, Tuple

import keyring
import requests
from pydantic import BaseModel

from arc_memory.errors import LinearAuthError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Constants
KEYRING_SERVICE = "arc-memory"
KEYRING_USERNAME = "linear-token"
LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_URL = "https://linear.app"
DEVICE_CODE_URL = f"{LINEAR_URL}/oauth/device/code"
DEVICE_TOKEN_URL = f"{LINEAR_URL}/oauth/token"
USER_AGENT = "Arc-Memory/0.2.2"

# Environment variable names
ENV_CLIENT_ID = "ARC_LINEAR_CLIENT_ID"
ENV_CLIENT_SECRET = "ARC_LINEAR_CLIENT_SECRET"


class LinearAppConfig(BaseModel):
    """Configuration for a Linear App."""

    client_id: str
    client_secret: str


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


def get_linear_app_config_from_env() -> Optional[LinearAppConfig]:
    """Get Linear App configuration from environment variables.

    Returns:
        The Linear App configuration, or None if not found.
    """
    client_id = os.environ.get(ENV_CLIENT_ID)
    client_secret = os.environ.get(ENV_CLIENT_SECRET)

    # Ensure we have all required values
    if not all([client_id, client_secret]):
        return None

    logger.info(f"Found Linear App configuration in environment variables (Client ID: {client_id})")
    return LinearAppConfig(
        client_id=client_id,
        client_secret=client_secret
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


def get_linear_token(token: Optional[str] = None, allow_failure: bool = False) -> Optional[str]:
    """Get a Linear token from various sources.

    Args:
        token: An explicit token to use. If None, tries to find a token from other sources.
        allow_failure: If True, returns None instead of raising an error when no token is found.

    Returns:
        A Linear token, or None if allow_failure is True and no token could be found.

    Raises:
        LinearAuthError: If no token could be found and allow_failure is False.
    """
    # Check explicit token
    if token:
        logger.info("Using explicitly provided Linear token")
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


def start_device_flow(client_id: str) -> Tuple[str, str, int]:
    """Start the Linear device flow authentication.

    Args:
        client_id: The Linear OAuth client ID.

    Returns:
        A tuple of (device_code, verification_uri, interval).

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

        return device_code, verification_uri, interval
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
