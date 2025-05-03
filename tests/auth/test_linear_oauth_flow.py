"""Integration tests for Linear OAuth flow."""

import unittest
from unittest.mock import MagicMock, patch

from arc_memory.auth.default_credentials import DEFAULT_LINEAR_CLIENT_ID, DEFAULT_LINEAR_CLIENT_SECRET
from arc_memory.auth.linear import (
    LinearAppConfig,
    LinearOAuthToken,
    exchange_code_for_token,
    start_oauth_flow,
)
from arc_memory.errors import LinearAuthError


class TestLinearOAuthFlow(unittest.TestCase):
    """Integration tests for Linear OAuth flow."""

    @patch("arc_memory.auth.linear.webbrowser.open")
    @patch("arc_memory.auth.linear.OAuthCallbackServer")
    @patch("arc_memory.auth.linear.exchange_code_for_token")
    @patch("arc_memory.auth.linear.store_oauth_token_in_keyring")
    @patch("arc_memory.auth.linear.validate_redirect_uri")
    def test_start_oauth_flow(self, mock_validate, mock_store, mock_exchange, mock_server, mock_browser):
        """Test the complete OAuth flow."""
        # Mock the redirect URI validation to always return True
        mock_validate.return_value = True

        # Mock the server
        mock_server_instance = MagicMock()
        mock_server_instance.wait_for_callback.return_value = ("test-code", None)
        # Set the port to match the one in the config to avoid redirect URI changes
        mock_server_instance.port = 3000
        mock_server.return_value = mock_server_instance

        # Mock the token exchange
        mock_token = LinearOAuthToken(
            access_token="test-token",
            token_type="Bearer",
            expires_in=3600,
            scope="read,write",
        )
        mock_exchange.return_value = mock_token

        # Mock the token storage
        mock_store.return_value = True

        # Mock the browser
        mock_browser.return_value = True

        # Create a config
        config = LinearAppConfig(
            client_id=DEFAULT_LINEAR_CLIENT_ID,
            client_secret=DEFAULT_LINEAR_CLIENT_SECRET,
            redirect_uri="http://localhost:3000/auth/linear/callback",
        )

        # Call the function
        result = start_oauth_flow(config, timeout=10)

        # Check the results
        self.assertEqual(result.access_token, "test-token")
        self.assertEqual(result.token_type, "Bearer")
        self.assertEqual(result.expires_in, 3600)
        self.assertEqual(result.scope, "read,write")

        # Check that the redirect URI was validated
        mock_validate.assert_called_once_with(config.redirect_uri)

        # Check that the server was started
        mock_server.assert_called_once()
        mock_server_instance.start.assert_called_once()

        # Check that the browser was opened
        mock_browser.assert_called_once()

        # Check that the token was exchanged
        mock_exchange.assert_called_once_with(config, "test-code")

        # Check that the token was stored
        mock_store.assert_called_once_with(mock_token)

    @patch("arc_memory.auth.linear.webbrowser.open")
    @patch("arc_memory.auth.linear.OAuthCallbackServer")
    @patch("arc_memory.auth.linear.validate_redirect_uri")
    def test_start_oauth_flow_error(self, mock_validate, mock_server, mock_browser):
        """Test error handling in the OAuth flow."""
        # Mock the redirect URI validation to always return True
        mock_validate.return_value = True

        # Mock the server
        mock_server_instance = MagicMock()
        mock_server_instance.wait_for_callback.return_value = (None, "Test error")
        # Set the port to match the one in the config to avoid redirect URI changes
        mock_server_instance.port = 3000
        mock_server.return_value = mock_server_instance

        # Mock the browser
        mock_browser.return_value = True

        # Create a config
        config = LinearAppConfig(
            client_id=DEFAULT_LINEAR_CLIENT_ID,
            client_secret=DEFAULT_LINEAR_CLIENT_SECRET,
            redirect_uri="http://localhost:3000/auth/linear/callback",
        )

        # Call the function and check that it raises an error
        with self.assertRaises(LinearAuthError):
            start_oauth_flow(config, timeout=10)

    @patch("arc_memory.auth.linear.requests.post")
    def test_exchange_code_for_token(self, mock_post):
        """Test exchanging an authorization code for a token."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "read,write",
        }
        mock_post.return_value = mock_response

        # Create a config
        config = LinearAppConfig(
            client_id=DEFAULT_LINEAR_CLIENT_ID,
            client_secret=DEFAULT_LINEAR_CLIENT_SECRET,
            redirect_uri="http://localhost:3000/auth/linear/callback",
        )

        # Call the function
        result = exchange_code_for_token(config, "test-code")

        # Check the results
        self.assertEqual(result.access_token, "test-token")
        self.assertEqual(result.token_type, "Bearer")
        self.assertEqual(result.expires_in, 3600)
        self.assertEqual(result.scope, "read,write")

        # Check that the request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://api.linear.app/oauth/token")
        self.assertEqual(kwargs["data"]["client_id"], DEFAULT_LINEAR_CLIENT_ID)
        self.assertEqual(kwargs["data"]["client_secret"], DEFAULT_LINEAR_CLIENT_SECRET)
        self.assertEqual(kwargs["data"]["code"], "test-code")
        self.assertEqual(kwargs["data"]["redirect_uri"], "http://localhost:3000/auth/linear/callback")
        self.assertEqual(kwargs["data"]["grant_type"], "authorization_code")

    @patch("arc_memory.auth.linear.requests.post")
    def test_exchange_code_for_token_error(self, mock_post):
        """Test error handling when exchanging a code for a token."""
        # Mock an error response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid authorization code",
        }
        mock_post.return_value = mock_response

        # Create a config
        config = LinearAppConfig(
            client_id=DEFAULT_LINEAR_CLIENT_ID,
            client_secret=DEFAULT_LINEAR_CLIENT_SECRET,
            redirect_uri="http://localhost:3000/auth/linear/callback",
        )

        # Call the function and check that it raises an error
        with self.assertRaises(LinearAuthError):
            exchange_code_for_token(config, "invalid-code")


if __name__ == "__main__":
    unittest.main()
