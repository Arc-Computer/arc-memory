"""Linear authentication for Arc Memory."""

import http.server
import base64
import hashlib
import json
import os
import secrets
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime
from typing import List, Optional, Tuple, Union

import keyring
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
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
LINEAR_API_BASE_URL = "https://api.linear.app"
DEVICE_CODE_URL = f"{LINEAR_URL}/oauth/device/code"
DEVICE_TOKEN_URL = f"{LINEAR_URL}/oauth/token"
OAUTH_AUTHORIZE_URL = f"{LINEAR_URL}/oauth/authorize"
OAUTH_TOKEN_URL = f"{LINEAR_API_BASE_URL}/oauth/token"  # Note: This is api.linear.app, not linear.app
OAUTH_REVOKE_URL = f"{LINEAR_API_BASE_URL}/oauth/revoke"
USER_AGENT = "Arc-Memory/0.4.1"

# Encryption constants
# Use a fixed salt for deterministic key derivation
# This is acceptable since we're only adding an extra layer of security on top of the system keyring
ENCRYPTION_SALT = b'arc_memory_linear_oauth'
# Derive a key from the machine's hostname and username for added security
# Use a more robust way to get machine identifier that works in CI environments
try:
    # Try to get username in a way that works in most environments
    username = os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'
    # Get hostname in a way that works in most environments
    hostname = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
    MACHINE_IDENTIFIER = f"{hostname}:{username}".encode()
except Exception:
    # Fallback for environments where the above doesn't work (like CI)
    MACHINE_IDENTIFIER = b'arc_memory_default_machine'

# Redirect URIs
PRODUCTION_REDIRECT_URI = "https://arc.computer/auth/linear/callback"
LOCAL_REDIRECT_URI = "http://localhost:3000/auth/linear/callback"
DEFAULT_REDIRECT_URI = LOCAL_REDIRECT_URI

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


def get_encryption_key() -> bytes:
    """Generate an encryption key based on machine-specific information.

    This provides an additional layer of security by making the encryption
    key specific to the current machine, so even if the encrypted token
    is copied to another machine, it cannot be decrypted.

    Returns:
        The encryption key as bytes.
    """
    # Use PBKDF2 to derive a key from the machine identifier
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = 256 bits
        salt=ENCRYPTION_SALT,
        iterations=100000,  # High number of iterations for security
    )
    key = base64.urlsafe_b64encode(kdf.derive(MACHINE_IDENTIFIER))
    return key


def encrypt_token(token_data: str) -> str:
    """Encrypt token data before storing it.

    Args:
        token_data: The token data to encrypt.

    Returns:
        The encrypted token data as a string.
    """
    try:
        # Generate the encryption key
        key = get_encryption_key()

        # Create a Fernet cipher with the key
        cipher = Fernet(key)

        # Encrypt the token data
        encrypted_data = cipher.encrypt(token_data.encode())

        # Return the encrypted data as a base64-encoded string
        return base64.urlsafe_b64encode(encrypted_data).decode()
    except Exception as e:
        logger.warning(f"Failed to encrypt token data: {e}")
        # Fall back to unencrypted data if encryption fails
        return token_data


def decrypt_token(encrypted_data: str) -> str:
    """Decrypt token data retrieved from storage.

    Args:
        encrypted_data: The encrypted token data.

    Returns:
        The decrypted token data as a string.
    """
    try:
        # Check if the data is base64-encoded (encrypted)
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
        except Exception:
            # If decoding fails, it's probably not encrypted
            return encrypted_data

        # Generate the encryption key
        key = get_encryption_key()

        # Create a Fernet cipher with the key
        cipher = Fernet(key)

        # Decrypt the token data
        decrypted_data = cipher.decrypt(decoded_data)

        # Return the decrypted data as a string
        return decrypted_data.decode()
    except Exception as e:
        logger.warning(f"Failed to decrypt token data: {e}")
        # Return the original data if decryption fails
        return encrypted_data


def get_oauth_token_from_keyring() -> Optional[LinearOAuthToken]:
    """Get a Linear OAuth token from the system keyring.

    Returns:
        The OAuth token, or None if not found.
    """
    try:
        encrypted_token_json = keyring.get_password(KEYRING_SERVICE, KEYRING_OAUTH_USERNAME)
        if encrypted_token_json:
            # Decrypt the token data
            token_json = decrypt_token(encrypted_token_json)
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

        # Encrypt the token data before storing
        encrypted_token_json = encrypt_token(token_json)

        keyring.set_password(KEYRING_SERVICE, KEYRING_OAUTH_USERNAME, encrypted_token_json)
        logger.info("Stored Linear OAuth token securely in system keyring")
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


def secure_client_secret(client_secret: str) -> str:
    """Securely handle a client secret.

    This function is a placeholder for more advanced security measures.
    In a production environment, consider using a secure vault service
    or hardware security module (HSM) to store and retrieve client secrets.

    Args:
        client_secret: The client secret to handle.

    Returns:
        The client secret (potentially transformed or retrieved from a secure source).
    """
    # In a real-world scenario, this function might:
    # 1. Retrieve the secret from a secure vault service
    # 2. Decrypt the secret using a hardware security module
    # 3. Apply additional security measures

    # For now, we just return the secret as-is
    return client_secret


def secure_clear_memory(sensitive_data: str) -> None:
    """Securely clear sensitive data from memory.

    This function attempts to securely clear sensitive data from memory
    to prevent it from being exposed in memory dumps or swap files.

    Note: This function has limitations due to Python's memory management.
    It may not completely remove all traces of sensitive data from memory
    due to string immutability, memory copying, and garbage collection behavior.

    Args:
        sensitive_data: The sensitive data to clear.
    """
    if not sensitive_data:
        return

    # For CI environments and safety, we'll use the reference replacement method
    # Direct memory access with ctypes can cause segmentation faults in some environments

    # Overwrite the reference with zeros
    sensitive_data = "0" * len(sensitive_data)

    # Delete the reference
    del sensitive_data

    # Suggest garbage collection
    import gc
    gc.collect()

    # Note: A more secure approach would be to use ctypes to directly access and zero memory,
    # but this can cause segmentation faults in some environments:
    #
    # import ctypes
    # location = id(sensitive_data) + 20  # CPython string header size
    # size = len(sensitive_data)
    # ctypes.memset(location, 0, size)
    #
    # This is left as a comment for documentation purposes.


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
        # Log the request details (without sensitive information)
        logger.debug(f"Exchanging code for token with client_id: {config.client_id}")
        logger.debug(f"Redirect URI: {config.redirect_uri}")
        logger.debug(f"Code length: {len(code)}")

        # Securely handle the client secret
        client_secret = secure_client_secret(config.client_secret)

        # Prepare the request data
        data = {
            "client_id": config.client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": config.redirect_uri,
            "grant_type": "authorization_code",
        }

        # Log the request URL and data (without sensitive information)
        logger.debug(f"POST request to: {OAUTH_TOKEN_URL}")
        logger.debug(f"Request data: client_id={config.client_id}, redirect_uri={config.redirect_uri}, grant_type=authorization_code")

        # Create headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",  # Linear OAuth token endpoint expects form data
            "User-Agent": USER_AGENT,
        }

        # Log the request headers
        logger.debug(f"Request headers: {headers}")

        # Make the request
        try:
            # Use form data as required by Linear OAuth token endpoint
            response = requests.post(
                OAUTH_TOKEN_URL,
                headers=headers,
                data=data,  # Use data parameter for form content
            )
        except Exception as e:
            logger.error(f"Exception during request: {e}")
            raise

        # Log the response status and headers
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")

        # Log the response content (for debugging)
        logger.debug(f"Response content: {response.text}")

        # If we got a 400 error, log more details
        if response.status_code == 400:
            logger.error(f"400 Bad Request error: {response.text}")
            try:
                error_data = response.json()
                logger.error(f"Error details: {error_data}")
            except Exception:
                logger.error("Could not parse error response as JSON")

        # Check for HTTP errors
        response.raise_for_status()

        # Parse the JSON response
        data = response.json()

        # Check for OAuth errors
        if "error" in data:
            error_msg = f"Token exchange error: {data.get('error_description', data['error'])}"
            logger.error(error_msg)
            raise LinearAuthError(error_msg)

        # Create and return the token
        token = LinearOAuthToken(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 315705599),  # Default to ~10 years if not provided
            scope=data.get("scope", "read"),
            created_at=datetime.now(),
        )

        logger.info("Successfully exchanged code for access token")

        # Securely clear sensitive data from memory
        secure_clear_memory(client_secret)
        secure_clear_memory(code)

        return token
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error during token exchange: {e}")
        # Securely clear sensitive data from memory
        secure_clear_memory(client_secret)
        secure_clear_memory(code)
        raise LinearAuthError(f"HTTP error during token exchange: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error during token exchange: {e}")
        # Securely clear sensitive data from memory
        secure_clear_memory(client_secret)
        secure_clear_memory(code)
        raise LinearAuthError(f"Request error during token exchange: {e}")
    except ValueError as e:
        logger.error(f"Invalid JSON response: {e}")
        # Securely clear sensitive data from memory
        secure_clear_memory(client_secret)
        secure_clear_memory(code)
        raise LinearAuthError(f"Invalid JSON response: {e}")
    except LinearAuthError:
        # Securely clear sensitive data from memory
        secure_clear_memory(client_secret)
        secure_clear_memory(code)
        # Re-raise LinearAuthError
        raise
    except Exception as e:
        logger.error(f"Failed to exchange code for token: {e}")
        # Securely clear sensitive data from memory
        secure_clear_memory(client_secret)
        secure_clear_memory(code)
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


def validate_client_id(client_id: str) -> bool:
    """Validate a Linear client ID.

    Args:
        client_id: The client ID to validate.

    Returns:
        True if the client ID is valid, False otherwise.
    """
    # Check for None or empty string
    if not client_id:
        return False

    # Linear client IDs are 32-character hexadecimal strings
    import re
    return bool(re.match(r'^[0-9a-f]{32}$', client_id))


def validate_redirect_uri(redirect_uri: str) -> bool:
    """Validate a redirect URI to prevent open redirect vulnerabilities.

    Args:
        redirect_uri: The redirect URI to validate.

    Returns:
        True if the redirect URI is valid, False otherwise.
    """
    # Check for None or empty string
    if not redirect_uri:
        return False

    # Parse the URI
    try:
        parsed = urllib.parse.urlparse(redirect_uri)

        # Check for required components
        if not parsed.scheme or not parsed.netloc:
            return False

        # Check for allowed schemes
        if parsed.scheme not in ["http", "https"]:
            return False

        # Check for allowed hosts
        allowed_hosts = ["localhost", "127.0.0.1", "arc.computer"]

        # Special case for localhost with port
        if ":" in parsed.netloc:
            host, port = parsed.netloc.rsplit(":", 1)
            if host == "localhost" and port.isdigit():
                return True

        # Check for exact matches or proper subdomains
        if not (parsed.netloc in allowed_hosts or
                any(parsed.netloc.endswith(f".{host}") and
                    not parsed.netloc.startswith(f".{host}")
                    for host in allowed_hosts)):
            return False

        # Check for allowed paths
        if not parsed.path.startswith("/auth/linear/callback"):
            return False

        return True
    except Exception:
        return False


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    # Class variables to store the authorization code and state
    authorization_code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None
    expected_state: Optional[str] = None
    callback_received = threading.Event()

    def do_GET(self) -> None:
        """Handle GET requests to the callback URL."""
        # Parse the query parameters
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        # Check for error
        if "error" in params:
            OAuthCallbackHandler.error = params["error"][0]
            self.send_error_response()
            return

        # Check for code and state
        if "code" in params and "state" in params:
            OAuthCallbackHandler.authorization_code = params["code"][0]
            OAuthCallbackHandler.state = params["state"][0]

            # Verify state parameter
            if OAuthCallbackHandler.state != OAuthCallbackHandler.expected_state:
                OAuthCallbackHandler.error = "Invalid state parameter (CSRF attack prevention)"
                self.send_error_response()
                return

            self.send_success_response()
        else:
            OAuthCallbackHandler.error = "Missing required parameters"
            self.send_error_response()

        # Signal that we've received the callback
        OAuthCallbackHandler.callback_received.set()

    def send_success_response(self) -> None:
        """Send a success response to the browser."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Arc Memory - Linear Authentication</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    text-align: center;
                }
                .success {
                    color: green;
                    font-weight: bold;
                }
                .info {
                    margin-top: 20px;
                    padding: 10px;
                    background-color: #f0f0f0;
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <h1>Arc Memory - Linear Authentication</h1>
            <p class="success">Authentication successful!</p>
            <p>You have successfully authenticated with Linear.</p>
            <p>You can now close this window and return to the Arc Memory CLI.</p>
            <div class="info">
                <p>This window will automatically close in 5 seconds.</p>
            </div>
            <script>
                setTimeout(function() {
                    window.close();
                }, 5000);
            </script>
        </body>
        </html>
        """

        self.wfile.write(html.encode())

    def send_error_response(self) -> None:
        """Send an error response to the browser."""
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Arc Memory - Linear Authentication Error</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    text-align: center;
                }}
                .error {{
                    color: red;
                    font-weight: bold;
                }}
                .info {{
                    margin-top: 20px;
                    padding: 10px;
                    background-color: #f0f0f0;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <h1>Arc Memory - Linear Authentication</h1>
            <p class="error">Authentication failed!</p>
            <p>Error: {OAuthCallbackHandler.error}</p>
            <p>Please try again or contact support if the issue persists.</p>
            <div class="info">
                <p>This window will automatically close in 10 seconds.</p>
            </div>
            <script>
                setTimeout(function() {{
                    window.close();
                }}, 10000);
            </script>
        </body>
        </html>
        """

        self.wfile.write(html.encode())

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger instead of printing to stderr."""
        logger.debug(f"OAuthCallbackHandler: {format % args}")

    @classmethod
    def reset(cls) -> None:
        """Reset the handler state."""
        cls.authorization_code = None
        cls.state = None
        cls.error = None
        cls.expected_state = None
        cls.callback_received.clear()


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use.

    Args:
        port: The port to check.

    Returns:
        True if the port is in use, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def find_free_port(start_port: int = 3000, max_attempts: int = 10) -> int:
    """Find a free port starting from the given port.

    Args:
        start_port: The port to start searching from.
        max_attempts: The maximum number of ports to check.

    Returns:
        A free port, or -1 if no free port was found.
    """
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    return -1


class OAuthCallbackServer:
    """Server to handle OAuth callbacks."""

    def __init__(self, host: str = "localhost", port: int = 3000, path: str = "/auth/linear/callback"):
        """Initialize the server.

        Args:
            host: The hostname to listen on.
            port: The port to listen on.
            path: The path to listen on.
        """
        self.host = host
        self.port = port
        self.path = path
        self.server: Optional[socketserver.TCPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def start(self, expected_state: str) -> None:
        """Start the server.

        Args:
            expected_state: The expected state parameter for CSRF protection.

        Raises:
            LinearAuthError: If the server could not be started.
        """
        # Reset the handler state
        OAuthCallbackHandler.reset()
        OAuthCallbackHandler.expected_state = expected_state

        # Check if the port is in use
        if is_port_in_use(self.port):
            logger.warning(f"Port {self.port} is already in use")

            # Try to find a free port
            free_port = find_free_port(self.port + 1)
            if free_port != -1:
                logger.info(f"Found free port: {free_port}")
                self.port = free_port
            else:
                raise LinearAuthError(
                    f"Port {self.port} is already in use and no free ports were found. "
                    "Please close any applications that might be using this port and try again."
                )

        # Create and start the server
        try:
            # Allow reuse of the address to avoid "Address already in use" errors
            socketserver.TCPServer.allow_reuse_address = True

            self.server = socketserver.TCPServer((self.host, self.port), OAuthCallbackHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True  # Don't keep the process alive
            self.server_thread.start()

            logger.info(f"Started OAuth callback server on http://{self.host}:{self.port}{self.path}")
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise LinearAuthError(f"Failed to start server on {self.host}:{self.port}: {e}")

    def stop(self) -> None:
        """Stop the server."""
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
                logger.info("Stopped OAuth callback server")
            except Exception as e:
                logger.warning(f"Failed to stop server: {e}")

    def wait_for_callback(self, timeout: int = 300) -> Tuple[Optional[str], Optional[str]]:
        """Wait for the callback to be received.

        Args:
            timeout: The timeout in seconds.

        Returns:
            A tuple of (authorization_code, error).
        """
        # Wait for the callback
        if OAuthCallbackHandler.callback_received.wait(timeout):
            return OAuthCallbackHandler.authorization_code, OAuthCallbackHandler.error
        else:
            return None, "Timeout waiting for authorization"


def start_oauth_flow(config: LinearAppConfig, timeout: int = 300) -> LinearOAuthToken:
    """Start the OAuth flow and wait for the callback.

    This function handles the complete OAuth 2.0 flow:
    1. Starts a local server to receive the callback
    2. Opens a browser for the user to authenticate
    3. Waits for the callback with the authorization code
    4. Exchanges the code for an access token
    5. Stores the token securely

    Args:
        config: The Linear App configuration.
        timeout: The timeout in seconds.

    Returns:
        The OAuth token.

    Raises:
        LinearAuthError: If the OAuth flow failed.
    """
    # Generate a secure state parameter for CSRF protection
    state = generate_secure_state()
    logger.debug("Generated secure state parameter for CSRF protection")

    # Validate the redirect URI
    if not validate_redirect_uri(config.redirect_uri):
        logger.error(f"Invalid redirect URI: {config.redirect_uri}")
        raise LinearAuthError(
            f"Invalid redirect URI: {config.redirect_uri}. "
            "The redirect URI must be a valid HTTP or HTTPS URL with an allowed host and path."
        )

    # Extract host, port, and path from redirect URI
    try:
        parsed_uri = urllib.parse.urlparse(config.redirect_uri)
        host = parsed_uri.hostname or "localhost"
        port = parsed_uri.port or 3000
        path = parsed_uri.path or "/auth/linear/callback"
        logger.debug(f"Using callback server at {host}:{port}{path}")
    except Exception as e:
        logger.error(f"Failed to parse redirect URI: {e}")
        raise LinearAuthError(f"Invalid redirect URI: {config.redirect_uri}. Error: {e}")

    # Start the callback server
    server = None
    try:
        server = OAuthCallbackServer(host=host, port=port, path=path)
        server.start(expected_state=state)

        # Store the original redirect URI for reference
        original_redirect_uri = config.redirect_uri

        # Check if the server is using a different port than the one in the redirect URI
        if server.port != port:
            # Update the redirect URI in the config using urlsplit/urlunsplit for better IPv6 support
            parsed = urllib.parse.urlsplit(config.redirect_uri)
            netloc = parsed.netloc

            # Handle IPv6 addresses correctly
            if ']' in netloc:  # IPv6 address format is [ipv6]:port
                # For IPv6, we need to handle the format [ipv6]:port
                if ':' in netloc.split(']', 1)[1]:
                    # If there's a port, split at the last colon after the closing bracket
                    host = netloc.rsplit(':', 1)[0]
                else:
                    # No port in the original URI
                    host = netloc
                netloc = f"{host}:{server.port}"
            else:
                # For regular hostnames, just split at the first colon
                if ':' in netloc:
                    host = netloc.split(':', 1)[0]
                else:
                    host = netloc
                netloc = f"{host}:{server.port}"

            # Rebuild the URI with the new port
            new_redirect_uri = urllib.parse.urlunsplit((
                parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment
            ))
            config.redirect_uri = new_redirect_uri


            # Provide a clear warning about the redirect URI mismatch
            logger.warning(f"PORT MISMATCH DETECTED: Using port {server.port} instead of {port} (which is in use)")
            logger.warning(f"Original redirect URI: {original_redirect_uri}")
            logger.warning(f"Updated redirect URI: {new_redirect_uri}")
            logger.warning("⚠️ IMPORTANT: This port change may cause authentication to fail if it doesn't match your Linear OAuth app settings.")
            logger.warning("To fix this, either:")
            logger.warning(f"  1. Update your Linear OAuth app settings to use the new redirect URI: {new_redirect_uri}")
            logger.warning(f"  2. Free up port {port} and try again")
            logger.warning(f"  3. Modify your configuration to use a different port that is available")
    except Exception as e:

        logger.error(f"Failed to start callback server: {e}")
        raise LinearAuthError(
            f"Failed to start callback server on {host}:{port}: {e}. "
            "This may be due to the port being in use. Try again or use a different port."
        )

    try:
        # Generate the authorization URL
        try:
            auth_url = generate_oauth_url(config, state=state)
            logger.debug(f"Generated authorization URL: {auth_url}")
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise LinearAuthError(f"Failed to generate authorization URL: {e}")

        # Open the browser
        logger.info(f"Opening browser to: {auth_url}")
        if not webbrowser.open(auth_url):
            logger.warning("Failed to open browser automatically")
            logger.info("Please open this URL manually in your browser:")
            logger.info(auth_url)

        # Wait for the callback
        logger.info(f"Waiting for callback (timeout: {timeout} seconds)...")
        code, error = server.wait_for_callback(timeout=timeout)

        if error:
            logger.error(f"OAuth flow error: {error}")
            raise LinearAuthError(
                f"OAuth flow failed: {error}. "
                "Please check your Linear OAuth application configuration and try again."
            )

        if not code:
            logger.error("No authorization code received")
            raise LinearAuthError(
                "No authorization code received. "
                "The authentication flow timed out or was cancelled. Please try again."
            )

        logger.info("Received authorization code, exchanging for token...")

        # Exchange the code for a token
        try:
            token = exchange_code_for_token(config, code)
            logger.info("Successfully exchanged authorization code for access token")
        except Exception as e:
            error_msg = str(e)
            if "redirect_uri" in error_msg.lower() and original_redirect_uri != config.redirect_uri:
                # Provide specific guidance for redirect URI mismatch errors
                logger.error(f"Failed to exchange code for token due to redirect URI mismatch: {e}")
                raise LinearAuthError(
                    f"Authentication failed due to redirect URI mismatch. The Linear OAuth app expected "
                    f"{original_redirect_uri} but we used {config.redirect_uri}.\n\n"
                    f"To fix this, either:\n"
                    f"1. Update your Linear OAuth app settings to use: {config.redirect_uri}\n"
                    f"2. Free up port {port} and try again\n"
                    f"3. Modify your configuration to use a different port that is available"
                )
            else:
                logger.error(f"Failed to exchange code for token: {e}")
                raise LinearAuthError(
                    f"Failed to exchange authorization code for access token: {e}. "
                    "Please check your Linear OAuth application configuration and try again."
                )

        # Store the token
        try:
            if store_oauth_token_in_keyring(token):
                logger.info("Successfully stored OAuth token in keyring")
            else:
                logger.warning("Failed to store OAuth token in keyring")
        except Exception as e:
            logger.warning(f"Failed to store OAuth token in keyring: {e}")

        return token
    finally:
        # Stop the server
        if server:
            try:
                server.stop()
                logger.debug("Stopped OAuth callback server")
            except Exception as e:
                logger.warning(f"Failed to stop callback server: {e}")
                # Don't raise an exception here, as we want to return the token if we have it
