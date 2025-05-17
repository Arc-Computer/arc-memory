"""Tests for the Jira authentication module."""

import json
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from arc_memory.auth.jira import (
    JiraAppConfig,
    JiraAuthError,
    JiraOAuthToken,
    decrypt_token,
    encrypt_token,
    exchange_code_for_token,
    generate_oauth_url,
    generate_pkce_verifier_and_challenge,
    generate_secure_state,
    get_encryption_key,
    get_jira_app_config_from_env,
    get_jira_token,
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


class TestJiraAuth(unittest.TestCase):
    """Tests for the Jira authentication module."""

    def setUp(self):
        """Set up test fixtures."""
        # Set up a test token
        self.test_token = "test_token"
        self.test_oauth_token = JiraOAuthToken(
            access_token="test_access_token",
            token_type="Bearer",
            refresh_token="test_refresh_token",
            scope="read:jira-user read:jira-work",
            created_at=datetime.now(),
        )
        self.test_app_config = JiraAppConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:3000/auth/jira/callback",
        )

        # Create a temporary environment with test values
        self.original_env = os.environ.copy()
        os.environ["JIRA_API_TOKEN"] = "test_env_token"
        os.environ["ARC_JIRA_CLIENT_ID"] = "test_env_client_id"
        os.environ["ARC_JIRA_CLIENT_SECRET"] = "test_env_client_secret"
        os.environ["ARC_JIRA_REDIRECT_URI"] = "http://localhost:3000/auth/jira/callback"
        os.environ["ARC_JIRA_CLOUD_ID"] = "test_cloud_id"

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
        os.environ.pop("JIRA_API_TOKEN")
        os.environ["JIRA_TOKEN"] = "test_jira_token"
        token = get_token_from_env()
        assert token == "test_jira_token"

        # Test with no environment variables
        os.environ.pop("JIRA_TOKEN")
        token = get_token_from_env()
        assert token is None

    @patch("arc_memory.auth.jira.keyring")
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

    @patch("arc_memory.auth.jira.keyring")
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
        assert token.refresh_token == "test_refresh_token"
        assert token.scope == "read:jira-user read:jira-work"
        mock_keyring.get_password.assert_called_once()

        # Test with no token in keyring
        mock_keyring.get_password.return_value = None
        token = get_oauth_token_from_keyring()
        assert token is None

        # Test with keyring error
        mock_keyring.get_password.side_effect = Exception("Keyring error")
        token = get_oauth_token_from_keyring()
        assert token is None

    def test_get_jira_app_config_from_env(self):
        """Test getting Jira App configuration from environment variables."""
        config = get_jira_app_config_from_env()
        assert config is not None
        assert config.client_id == "test_env_client_id"
        assert config.client_secret == "test_env_client_secret"
        assert config.redirect_uri == "http://localhost:3000/auth/jira/callback"
        assert config.cloud_id == "test_cloud_id"

        # Test with missing environment variables
        os.environ.pop("ARC_JIRA_CLIENT_ID")
        config = get_jira_app_config_from_env()
        assert config is None

    @patch("arc_memory.auth.jira.keyring")
    def test_store_token_in_keyring(self, mock_keyring):
        """Test storing a token in the system keyring."""
        result = store_token_in_keyring(self.test_token)
        assert result is True
        mock_keyring.set_password.assert_called_once()

        # Test with keyring error
        mock_keyring.set_password.side_effect = Exception("Keyring error")
        result = store_token_in_keyring(self.test_token)
        assert result is False

    @patch("arc_memory.auth.jira.keyring")
    def test_store_oauth_token_in_keyring(self, mock_keyring):
        """Test storing an OAuth token in the system keyring."""
        result = store_oauth_token_in_keyring(self.test_oauth_token)
        assert result is True
        mock_keyring.set_password.assert_called_once()

        # Test with keyring error
        mock_keyring.set_password.side_effect = Exception("Keyring error")
        result = store_oauth_token_in_keyring(self.test_oauth_token)
        assert result is False

    @patch("arc_memory.auth.jira.get_oauth_token_from_keyring")
    @patch("arc_memory.auth.jira.get_token_from_env")
    @patch("arc_memory.auth.jira.get_token_from_keyring")
    def test_get_jira_token(self, mock_get_token_from_keyring, mock_get_token_from_env, mock_get_oauth_token_from_keyring):
        """Test getting a Jira token from various sources."""
        # Test with explicit token
        token = get_jira_token(token="explicit_token")
        assert token == "explicit_token"

        # Test with OAuth token
        mock_oauth_token = MagicMock()
        mock_oauth_token.is_expired.return_value = False
        mock_oauth_token.access_token = "oauth_token"
        mock_get_oauth_token_from_keyring.return_value = mock_oauth_token
        token = get_jira_token(prefer_oauth=True)
        assert token == "oauth_token"

        # Test with expired OAuth token
        mock_oauth_token.is_expired.return_value = True
        mock_get_token_from_env.return_value = "env_token"
        token = get_jira_token(prefer_oauth=True)
        assert token == "env_token"

        # Test without OAuth token
        mock_get_oauth_token_from_keyring.return_value = None
        token = get_jira_token(prefer_oauth=True)
        assert token == "env_token"

        # Test with no OAuth and no env token
        mock_get_token_from_env.return_value = None
        mock_get_token_from_keyring.return_value = "keyring_token"
        token = get_jira_token(prefer_oauth=True)
        assert token == "keyring_token"

        # Test with no tokens and allow_failure=True
        mock_get_token_from_keyring.return_value = None
        token = get_jira_token(allow_failure=True)
        assert token is None

        # Test with no tokens and allow_failure=False
        with pytest.raises(JiraAuthError):
            get_jira_token(allow_failure=False)

    def test_validate_client_id(self):
        """Test validating a Jira client ID."""
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
        assert validate_redirect_uri("http://localhost:3000/auth/jira/callback") is True
        assert validate_redirect_uri("https://arc.computer/auth/jira/callback") is True
        assert validate_redirect_uri("https://subdomain.arc.computer/auth/jira/callback") is True

        # Test with invalid redirect URIs
        assert validate_redirect_uri("") is False
        assert validate_redirect_uri(None) is False
        assert validate_redirect_uri("not_a_url") is False
        assert validate_redirect_uri("http://localhost") is False  # No path
        assert validate_redirect_uri("http://localhost/wrong/path") is False  # Wrong path
        assert validate_redirect_uri("http://evil.com/auth/jira/callback") is False  # Not allowed host
        assert validate_redirect_uri("ftp://localhost/auth/jira/callback") is False  # Not allowed scheme

    def test_generate_pkce_verifier_and_challenge(self):
        """Test generating PKCE verifier and challenge."""
        verifier, challenge, method = generate_pkce_verifier_and_challenge()
        assert verifier is not None
        assert challenge is not None
        assert method == "S256"
        assert len(verifier) > 0
        assert len(challenge) > 0
        assert verifier != challenge

    def test_generate_oauth_url(self):
        """Test generating an OAuth authorization URL."""
        verifier, challenge, method = generate_pkce_verifier_and_challenge()
        url = generate_oauth_url(self.test_app_config, challenge, method)
        assert "client_id=test_client_id" in url
        assert "redirect_uri=http%3A//localhost%3A3000/auth/jira/callback" in url
        assert "response_type=code" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url

        # Test with state parameter
        url = generate_oauth_url(self.test_app_config, challenge, method, state="test_state")
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


if __name__ == "__main__":
    unittest.main()
