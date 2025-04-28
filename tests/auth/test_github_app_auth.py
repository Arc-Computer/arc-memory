"""Tests for GitHub App authentication."""

import unittest
from unittest.mock import MagicMock, patch

from arc_memory.auth.github import (
    GitHubAppConfig,
    get_installation_token_for_repo,
    store_github_app_config_in_keyring,
    get_github_app_config_from_keyring,
    get_github_app_config_from_env,
    create_jwt,
    get_installation_id,
    get_installation_token,
)
from arc_memory.errors import GitHubAuthError


class TestGitHubAppAuth(unittest.TestCase):
    """Tests for GitHub App authentication."""

    def test_github_app_config(self):
        """Test creating a GitHub App config."""
        config = GitHubAppConfig(
            app_id="test-app-id",
            private_key="test-private-key",
            client_id="1234567890abcdef1234",  # Valid format client ID
            client_secret="test-client-secret",
        )

        self.assertEqual(config.app_id, "test-app-id")
        self.assertEqual(config.private_key, "test-private-key")
        self.assertEqual(config.client_id, "1234567890abcdef1234")
        self.assertEqual(config.client_secret, "test-client-secret")

    @patch("arc_memory.auth.github.keyring")
    def test_store_github_app_config_in_keyring(self, mock_keyring):
        """Test storing a GitHub App config in the keyring."""
        mock_keyring.set_password.return_value = None

        config = GitHubAppConfig(
            app_id="test-app-id",
            private_key="test-private-key",
            client_id="1234567890abcdef1234",  # Valid format client ID
            client_secret="test-client-secret",
        )

        result = store_github_app_config_in_keyring(config)

        self.assertTrue(result)
        mock_keyring.set_password.assert_called()

    @patch("arc_memory.auth.github.keyring")
    def test_get_github_app_config_from_keyring(self, mock_keyring):
        """Test getting a GitHub App config from the keyring."""
        mock_keyring.get_password.return_value = '{"app_id": "test-app-id", "private_key": "test-private-key", "client_id": "1234567890abcdef1234", "client_secret": "test-client-secret"}'

        config = get_github_app_config_from_keyring()

        self.assertIsNotNone(config)
        self.assertEqual(config.app_id, "test-app-id")
        self.assertEqual(config.private_key, "test-private-key")
        self.assertEqual(config.client_id, "1234567890abcdef1234")
        self.assertEqual(config.client_secret, "test-client-secret")

    @patch("arc_memory.auth.github.os.environ")
    def test_get_github_app_config_from_env(self, mock_environ):
        """Test getting a GitHub App config from environment variables."""
        mock_environ.get.side_effect = lambda key: {
            "ARC_GITHUB_APP_ID": "test-app-id",
            "ARC_GITHUB_PRIVATE_KEY_PATH": "/path/to/private/key",
            "ARC_GITHUB_CLIENT_ID": "1234567890abcdef1234",
            "ARC_GITHUB_CLIENT_SECRET": "test-client-secret",
        }.get(key)

        with patch("builtins.open", unittest.mock.mock_open(read_data="test-private-key")):
            config = get_github_app_config_from_env()

        self.assertIsNotNone(config)
        self.assertEqual(config.app_id, "test-app-id")
        self.assertEqual(config.private_key, "test-private-key")
        self.assertEqual(config.client_id, "1234567890abcdef1234")
        self.assertEqual(config.client_secret, "test-client-secret")

    @patch("arc_memory.auth.github.jwt.encode")
    def test_create_jwt(self, mock_jwt_encode):
        """Test creating a JWT for GitHub App authentication."""
        mock_jwt_encode.return_value = "test-jwt-token"

        token = create_jwt("test-app-id", "test-private-key")

        self.assertEqual(token, "test-jwt-token")
        mock_jwt_encode.assert_called_once()

    @patch("arc_memory.auth.github.requests.get")
    @patch("arc_memory.auth.github.create_jwt")
    def test_get_installation_id(self, mock_create_jwt, mock_requests_get):
        """Test getting an installation ID for a GitHub App."""
        mock_create_jwt.return_value = "test-jwt-token"

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 12345}
        mock_requests_get.return_value = mock_response

        installation_id = get_installation_id("test-app-id", "test-private-key", "test-owner", "test-repo")

        self.assertEqual(installation_id, "12345")
        mock_create_jwt.assert_called_once_with("test-app-id", "test-private-key")
        mock_requests_get.assert_called_once()

    @patch("arc_memory.auth.github.requests.post")
    @patch("arc_memory.auth.github.create_jwt")
    def test_get_installation_token(self, mock_create_jwt, mock_requests_post):
        """Test getting an installation token for a GitHub App."""
        mock_create_jwt.return_value = "test-jwt-token"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "token": "test-installation-token",
            "expires_at": "2025-04-28T00:00:00Z"
        }
        mock_requests_post.return_value = mock_response

        token, expires_at = get_installation_token("test-app-id", "test-private-key", "12345")

        self.assertEqual(token, "test-installation-token")
        self.assertIsNotNone(expires_at)
        mock_create_jwt.assert_called_once_with("test-app-id", "test-private-key")
        mock_requests_post.assert_called_once()

    @patch("arc_memory.auth.github.get_installation_token")
    @patch("arc_memory.auth.github.get_installation_id")
    @patch("arc_memory.auth.github.get_github_app_config")
    def test_get_installation_token_for_repo(self, mock_get_config, mock_get_id, mock_get_token):
        """Test getting an installation token for a repository."""
        mock_config = MagicMock()
        mock_config.app_id = "test-app-id"
        mock_config.private_key = "test-private-key"
        mock_get_config.return_value = mock_config

        mock_get_id.return_value = "12345"
        mock_get_token.return_value = ("test-installation-token", None)

        token = get_installation_token_for_repo("test-owner", "test-repo")

        self.assertEqual(token, "test-installation-token")
        mock_get_config.assert_called_once()
        mock_get_id.assert_called_once_with("test-app-id", "test-private-key", "test-owner", "test-repo")
        mock_get_token.assert_called_once_with("test-app-id", "test-private-key", "12345")


if __name__ == "__main__":
    unittest.main()
