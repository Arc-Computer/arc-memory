"""Tests for the Notion authentication module."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from arc_memory.auth.notion import (
    NotionAppConfig,
    NotionError,
    NotionOAuthToken,
    decrypt_token,
    encrypt_token,
    exchange_code_for_token,
    generate_oauth_url,
    generate_secure_state,
    get_encryption_key,
    get_notion_app_config_from_env,
    get_notion_token,
    get_oauth_token_from_keyring,
    get_token_from_env,
    get_token_from_keyring,
    is_port_in_use,
    start_oauth_flow,
    store_oauth_token_in_keyring,
    store_token_in_keyring,
    validate_client_id,
    validate_redirect_uri,
)
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


class TestNotionAuth(unittest.TestCase):
    """Tests for the Notion authentication module."""

    def setUp(self):
        """Set up test fixtures."""
        # Set up a test token
        self.test_token = "test_token"
        self.test_oauth_token = NotionOAuthToken(
            access_token="test_access_token",
            bot_id="test_bot_id",
            workspace_id="test_workspace_id",
            workspace_name="test_workspace_name",
            created_at=datetime.now(),
        )
        self.test_app_config = NotionAppConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:3000/auth/notion/callback",
        )

        # Create a temporary environment with test values
        self.original_env = os.environ.copy()
        os.environ["NOTION_API_KEY"] = "test_env_token"
        os.environ["ARC_NOTION_CLIENT_ID"] = "test_env_client_id"
        os.environ["ARC_NOTION_CLIENT_SECRET"] = "test_env_client_secret"
        os.environ["ARC_NOTION_REDIRECT_URI"] = "http://localhost:3000/auth/notion/callback"

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore the original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_get_token_from_env(self):
        """Test getting a token from environment variables."""
        token = get_token_from_env()
        assert token == "test_env_token"

        # Test with a different environment variable
        os.environ.pop("NOTION_API_KEY")
        os.environ["NOTION_TOKEN"] = "test_notion_token"
        token = get_token_from_env()
        assert token == "test_notion_token"

        # Test with no environment variables
        os.environ.pop("NOTION_TOKEN")
        token = get_token_from_env()
        assert token is None

    @patch("arc_memory.auth.notion.keyring")
    def test_get_token_from_keyring(self, mock_keyring):
        """Test getting a token from the system keyring."""
        mock_keyring.get_password.return_value = self.test_token
        token = get_token_from_keyring()
        assert token == self.test_token
        mock_keyring.get_password.assert_called_once()

        # Test with no token in keyring
        mock_keyring.get_password.return_value = None
        token = get_token_from_keyring()
        assert token is None

        # Test with keyring error
        mock_keyring.get_password.side_effect = Exception("Keyring error")
        token = get_token_from_keyring()
        assert token is None

    def test_get_encryption_key(self):
        """Test generating an encryption key."""
        key = get_encryption_key()
        assert key is not None
        assert isinstance(key, bytes)
        assert len(key) > 0

        # Test that the key is deterministic
        key2 = get_encryption_key()
        assert key == key2

    def test_encrypt_decrypt_token(self):
        """Test encrypting and decrypting a token."""
        # Create a test token data
        token_data = json.dumps({"access_token": "test_token"})

        # Encrypt it
        encrypted = encrypt_token(token_data)
        assert encrypted != token_data

        # Decrypt it
        decrypted = decrypt_token(encrypted)
        assert decrypted == token_data

        # Test decrypting non-encrypted data
        decrypted = decrypt_token("not_encrypted")
        assert decrypted == "not_encrypted"

    @patch("arc_memory.auth.notion.keyring")
    def test_get_oauth_token_from_keyring(self, mock_keyring):
        """Test getting an OAuth token from the system keyring."""
        # Create a test token JSON
        token_dict = self.test_oauth_token.model_dump()
        token_dict["created_at"] = token_dict["created_at"].isoformat()
        token_json = json.dumps(token_dict)
        encrypted_token_json = encrypt_token(token_json)

        # Set up the mock
        mock_keyring.get_password.return_value = encrypted_token_json

        # Test getting the token
        token = get_oauth_token_from_keyring()
        assert token is not None
        assert token.access_token == "test_access_token"
        assert token.bot_id == "test_bot_id"
        assert token.workspace_id == "test_workspace_id"
        mock_keyring.get_password.assert_called_once()

        # Test with no token in keyring
        mock_keyring.get_password.return_value = None
        token = get_oauth_token_from_keyring()
        assert token is None

        # Test with keyring error
        mock_keyring.get_password.side_effect = Exception("Keyring error")
        token = get_oauth_token_from_keyring()
        assert token is None

    def test_get_notion_app_config_from_env(self):
        """Test getting Notion App configuration from environment variables."""
        config = get_notion_app_config_from_env()
        assert config is not None
        assert config.client_id == "test_env_client_id"
        assert config.client_secret == "test_env_client_secret"
        assert config.redirect_uri == "http://localhost:3000/auth/notion/callback"

        # Test with missing environment variables
        os.environ.pop("ARC_NOTION_CLIENT_ID")
        config = get_notion_app_config_from_env()
        assert config is None

    @patch("arc_memory.auth.notion.keyring")
    def test_store_token_in_keyring(self, mock_keyring):
        """Test storing a token in the system keyring."""
        result = store_token_in_keyring(self.test_token)
        assert result is True
        mock_keyring.set_password.assert_called_once()

        # Test with keyring error
        mock_keyring.set_password.side_effect = Exception("Keyring error")
        result = store_token_in_keyring(self.test_token)
        assert result is False

    @patch("arc_memory.auth.notion.keyring")
    def test_store_oauth_token_in_keyring(self, mock_keyring):
        """Test storing an OAuth token in the system keyring."""
        result = store_oauth_token_in_keyring(self.test_oauth_token)
        assert result is True
        mock_keyring.set_password.assert_called_once()

        # Test with keyring error
        mock_keyring.set_password.side_effect = Exception("Keyring error")
        result = store_oauth_token_in_keyring(self.test_oauth_token)
        assert result is False

    @patch("arc_memory.auth.notion.get_oauth_token_from_keyring")
    @patch("arc_memory.auth.notion.get_token_from_env")
    @patch("arc_memory.auth.notion.get_token_from_keyring")
    def test_get_notion_token(self, mock_get_token_from_keyring, mock_get_token_from_env, mock_get_oauth_token_from_keyring):
        """Test getting a Notion token from various sources."""
        # Test with explicit token
        token = get_notion_token(token="explicit_token")
        assert token == "explicit_token"

        # Test with OAuth token
        mock_oauth_token = MagicMock()
        mock_oauth_token.is_expired.return_value = False
        mock_oauth_token.access_token = "oauth_token"
        mock_get_oauth_token_from_keyring.return_value = mock_oauth_token
        token = get_notion_token(prefer_oauth=True)
        assert token == "oauth_token"

        # Test with expired OAuth token
        mock_oauth_token.is_expired.return_value = True
        mock_get_token_from_env.return_value = "env_token"
        token = get_notion_token(prefer_oauth=True)
        assert token == "env_token"

        # Test without OAuth token
        mock_get_oauth_token_from_keyring.return_value = None
        token = get_notion_token(prefer_oauth=True)
        assert token == "env_token"

        # Test with no OAuth and no env token
        mock_get_token_from_env.return_value = None
        mock_get_token_from_keyring.return_value = "keyring_token"
        token = get_notion_token(prefer_oauth=True)
        assert token == "keyring_token"

        # Test with no tokens and allow_failure=True
        mock_get_token_from_keyring.return_value = None
        token = get_notion_token(allow_failure=True)
        assert token is None

        # Test with no tokens and allow_failure=False
        with pytest.raises(NotionError):
            get_notion_token(allow_failure=False)

    def test_validate_client_id(self):
        """Test validating a Notion client ID."""
        # Test with valid client ID
        assert validate_client_id("a" * 32) is True
        assert validate_client_id("1234567890abcdef") is True

        # Test with invalid client ID
        assert validate_client_id("") is False
        assert validate_client_id(None) is False
        assert validate_client_id("abc") is False  # Too short

    def test_validate_redirect_uri(self):
        """Test validating a redirect URI."""
        # Test with valid redirect URIs
        assert validate_redirect_uri("http://localhost:3000/auth/notion/callback") is True
        assert validate_redirect_uri("https://arc.computer/auth/notion/callback") is True
        assert validate_redirect_uri("https://subdomain.arc.computer/auth/notion/callback") is True

        # Test with invalid redirect URIs
        assert validate_redirect_uri("") is False
        assert validate_redirect_uri(None) is False
        assert validate_redirect_uri("not_a_url") is False
        assert validate_redirect_uri("http://localhost") is False  # No path
        assert validate_redirect_uri("http://localhost/wrong/path") is False  # Wrong path
        assert validate_redirect_uri("http://evil.com/auth/notion/callback") is False  # Not allowed host
        assert validate_redirect_uri("ftp://localhost/auth/notion/callback") is False  # Not allowed scheme

    def test_generate_oauth_url(self):
        """Test generating an OAuth authorization URL."""
        url = generate_oauth_url(self.test_app_config)
        assert "client_id=test_client_id" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fnotion%2Fcallback" in url
        assert "response_type=code" in url
        assert "owner=user" in url

        # Test with state parameter
        url = generate_oauth_url(self.test_app_config, state="test_state")
        assert "state=test_state" in url

    def test_generate_secure_state(self):
        """Test generating a secure state parameter."""
        state = generate_secure_state()
        assert state is not None
        assert isinstance(state, str)
        assert len(state) > 0

        # Test that each state is unique
        state2 = generate_secure_state()
        assert state != state2

    def test_is_port_in_use(self):
        """Test checking if a port is in use."""
        # This test is a bit tricky since we don't want to actually bind to ports
        # We'll just make sure the function doesn't crash
        result = is_port_in_use(12345)  # Unlikely to be in use
        assert isinstance(result, bool)

    @patch("arc_memory.auth.notion.requests.post")
    def test_exchange_code_for_token_success(self, mock_post):
        """Test exchanging an authorization code for an access token."""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "bot_id": "test_bot_id",
            "workspace_id": "test_workspace_id",
            "workspace_name": "test_workspace_name",
        }
        mock_post.return_value = mock_response

        # Call the function
        token = exchange_code_for_token(self.test_app_config, "test_code")

        # Verify the result
        assert token.access_token == "test_access_token"
        assert token.bot_id == "test_bot_id"
        assert token.workspace_id == "test_workspace_id"
        assert token.workspace_name == "test_workspace_name"

        # Verify the mock was called correctly
        mock_post.assert_called_once()
        # Check authorization header (Basic auth)
        args, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"].startswith("Basic ")
        # Check we're calling the right URL
        assert args[0] == "https://api.notion.com/v1/oauth/token"

    @patch("arc_memory.auth.notion.requests.post")
    def test_exchange_code_for_token_http_error(self, mock_post):
        """Test exchanging an authorization code for an access token with HTTP error."""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Bad Request")
        mock_response.text = '{"error": "invalid_grant", "error_description": "Invalid code"}'
        mock_response.json.return_value = {"error": "invalid_grant", "error_description": "Invalid code"}
        mock_post.return_value = mock_response

        # Call the function and expect an error
        with pytest.raises(NotionError) as excinfo:
            exchange_code_for_token(self.test_app_config, "test_code")

        # Verify the error message
        assert "HTTP error" in str(excinfo.value)

    @patch("arc_memory.auth.notion.requests.post")
    def test_exchange_code_for_token_missing_field(self, mock_post):
        """Test exchanging an authorization code for an access token with missing field."""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Missing required field workspace_id
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "bot_id": "test_bot_id",
        }
        mock_post.return_value = mock_response

        # Call the function and expect an error
        with pytest.raises(NotionError) as excinfo:
            exchange_code_for_token(self.test_app_config, "test_code")

        # Verify the error message
        assert "Missing required field" in str(excinfo.value)

    @patch("arc_memory.auth.notion.requests.post")
    def test_exchange_code_for_token_oauth_error(self, mock_post):
        """Test exchanging an authorization code for an access token with OAuth error."""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid code",
        }
        mock_post.return_value = mock_response

        # Call the function and expect an error
        with pytest.raises(NotionError) as excinfo:
            exchange_code_for_token(self.test_app_config, "test_code")

        # Verify the error message
        assert "Token exchange error" in str(excinfo.value)

    @patch("arc_memory.auth.notion.OAuthCallbackServer")
    @patch("arc_memory.auth.notion.webbrowser")
    @patch("arc_memory.auth.notion.exchange_code_for_token")
    @patch("arc_memory.auth.notion.store_oauth_token_in_keyring")
    def test_start_oauth_flow_success(self, mock_store, mock_exchange, mock_webbrowser, mock_server_class):
        """Test starting the OAuth flow."""
        # Set up the mock server
        mock_server = MagicMock()
        mock_server.wait_for_callback.return_value = ("test_code", None)
        mock_server_class.return_value = mock_server

        # Set up the mock token exchange
        mock_exchange.return_value = self.test_oauth_token

        # Set up the mock browser
        mock_webbrowser.open.return_value = True

        # Set up the mock storage
        mock_store.return_value = True

        # Call the function
        token = start_oauth_flow(self.test_app_config)

        # Verify the result
        assert token == self.test_oauth_token

        # Verify the mocks were called correctly
        mock_server.start.assert_called_once()
        mock_webbrowser.open.assert_called_once()
        mock_exchange.assert_called_once_with(self.test_app_config, "test_code")
        mock_store.assert_called_once_with(self.test_oauth_token)
        mock_server.stop.assert_called_once()

    @patch("arc_memory.auth.notion.OAuthCallbackServer")
    @patch("arc_memory.auth.notion.webbrowser")
    def test_start_oauth_flow_error(self, mock_webbrowser, mock_server_class):
        """Test starting the OAuth flow with an error."""
        # Set up the mock server
        mock_server = MagicMock()
        mock_server.wait_for_callback.return_value = (None, "Test error")
        mock_server_class.return_value = mock_server

        # Set up the mock browser
        mock_webbrowser.open.return_value = True

        # Call the function and expect an error
        with pytest.raises(NotionError) as excinfo:
            start_oauth_flow(self.test_app_config)

        # Verify the error message
        assert "OAuth flow failed: Test error" in str(excinfo.value)

        # Verify the mocks were called correctly
        mock_server.start.assert_called_once()
        mock_webbrowser.open.assert_called_once()
        mock_server.stop.assert_called_once()

    @patch("arc_memory.auth.notion.OAuthCallbackServer")
    @patch("arc_memory.auth.notion.webbrowser")
    def test_start_oauth_flow_timeout(self, mock_webbrowser, mock_server_class):
        """Test starting the OAuth flow with a timeout."""
        # Set up the mock server
        mock_server = MagicMock()
        mock_server.wait_for_callback.return_value = (None, None)
        mock_server_class.return_value = mock_server

        # Set up the mock browser
        mock_webbrowser.open.return_value = True

        # Call the function and expect an error
        with pytest.raises(NotionError) as excinfo:
            start_oauth_flow(self.test_app_config)

        # Verify the error message
        assert "No authorization code received" in str(excinfo.value)

        # Verify the mocks were called correctly
        mock_server.start.assert_called_once()
        mock_webbrowser.open.assert_called_once()
        mock_server.stop.assert_called_once()

    def test_oauth_token_is_expired(self):
        """Test checking if an OAuth token is expired."""
        # Create a token that's not expired
        token = NotionOAuthToken(
            access_token="test_access_token",
            bot_id="test_bot_id",
            workspace_id="test_workspace_id",
            created_at=datetime.now(),
            expires_in=3600,  # 1 hour
        )
        assert token.is_expired() is False

        # Create a token that's expired
        token = NotionOAuthToken(
            access_token="test_access_token",
            bot_id="test_bot_id",
            workspace_id="test_workspace_id",
            created_at=datetime.now() - timedelta(hours=2),
            expires_in=3600,  # 1 hour
        )
        assert token.is_expired() is True


if __name__ == "__main__":
    unittest.main()