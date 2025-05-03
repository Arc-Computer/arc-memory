"""Tests for Linear authentication."""

import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from arc_memory.auth.default_credentials import DEFAULT_LINEAR_CLIENT_ID, DEFAULT_LINEAR_CLIENT_SECRET
from arc_memory.auth.linear import (
    LinearAppConfig,
    LinearOAuthToken,
    exchange_code_for_token,
    generate_oauth_url,
    generate_secure_state,
    get_linear_token,
    get_oauth_token_from_keyring,
    start_device_flow,
    start_oauth_flow,
    store_oauth_token_in_keyring,
    validate_client_id,
)
from arc_memory.errors import LinearAuthError


class TestLinearAuth(unittest.TestCase):
    """Tests for Linear authentication."""

    @patch("arc_memory.auth.linear.requests.post")
    def test_start_device_flow(self, mock_post):
        """Test starting the device flow."""
        # Mock the response from Linear
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "device_code": "test-device-code",
            "user_code": "TEST-CODE",
            "verification_uri": "https://linear.app/oauth/device",
            "interval": 5,
        }
        mock_post.return_value = mock_response

        # Call the function with a valid format client ID
        valid_test_client_id = "abfe4960313bddfa75a59c37687aca0e"  # Valid format that passes our validation
        device_code, user_code, verification_uri, interval = start_device_flow(valid_test_client_id)

        # Check the results
        self.assertEqual(device_code, "test-device-code")
        self.assertEqual(user_code, "TEST-CODE")
        self.assertEqual(verification_uri, "https://linear.app/oauth/device")
        self.assertEqual(interval, 5)

        # Check that the request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://linear.app/oauth/device/code")
        self.assertEqual(kwargs["json"]["client_id"], valid_test_client_id)
        self.assertEqual(kwargs["json"]["scope"], "read,issues:read,issues:write")

    @patch("arc_memory.auth.linear.requests.post")
    def test_start_device_flow_error(self, mock_post):
        """Test error handling when starting the device flow."""
        # Mock an error response
        mock_post.side_effect = Exception("Test error")

        # Call the function and check that it raises an error
        with self.assertRaises(LinearAuthError):
            # Use a valid format client ID to ensure we're testing the API error, not validation
            valid_test_client_id = "abfe4960313bddfa75a59c37687aca0e"
            start_device_flow(valid_test_client_id)

    def test_default_client_id(self):
        """Test that the default client ID is set."""
        # This test will fail if DEFAULT_LINEAR_CLIENT_ID is not set
        # or if it's set to the placeholder value
        self.assertIsNotNone(DEFAULT_LINEAR_CLIENT_ID)
        self.assertNotEqual(DEFAULT_LINEAR_CLIENT_ID, "")

        # This check ensures we're not using the placeholder value
        self.assertNotEqual(DEFAULT_LINEAR_CLIENT_ID, "YOUR_LINEAR_CLIENT_ID")
        self.assertNotEqual(DEFAULT_LINEAR_CLIENT_ID, "placeholder_linear_client_id")

    def test_default_client_secret(self):
        """Test that the default client secret is set."""
        # This test will fail if DEFAULT_LINEAR_CLIENT_SECRET is not set
        # or if it's set to the placeholder value
        self.assertIsNotNone(DEFAULT_LINEAR_CLIENT_SECRET)
        self.assertNotEqual(DEFAULT_LINEAR_CLIENT_SECRET, "")

        # This check ensures we're not using the placeholder value
        self.assertNotEqual(DEFAULT_LINEAR_CLIENT_SECRET, "YOUR_DEFAULT_CLIENT_SECRET")

    def test_validate_client_id(self):
        """Test client ID validation."""
        # Valid client IDs
        self.assertTrue(validate_client_id("abfe4960313bddfa75a59c37687aca0e"))
        self.assertTrue(validate_client_id("1234567890abcdef1234567890abcdef"))

        # Invalid client IDs
        self.assertFalse(validate_client_id(""))
        self.assertFalse(validate_client_id(None))
        self.assertFalse(validate_client_id("short"))
        self.assertFalse(validate_client_id("ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"))  # Not lowercase hex

    def test_generate_secure_state(self):
        """Test generating a secure state parameter."""
        state = generate_secure_state()
        self.assertIsNotNone(state)
        self.assertGreaterEqual(len(state), 32)  # Should be at least 32 characters

        # Generate another state and ensure it's different
        state2 = generate_secure_state()
        self.assertNotEqual(state, state2)

    def test_generate_oauth_url(self):
        """Test generating an OAuth URL."""
        config = LinearAppConfig(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost:3000/callback",
            scopes=["read", "write"]
        )
        state = "test-state"

        url = generate_oauth_url(config, state=state)

        # Check that the URL contains all required parameters
        self.assertIn("client_id=test-client-id", url)
        self.assertIn("redirect_uri=http://localhost:3000/callback", url)
        self.assertIn("response_type=code", url)
        self.assertIn("scope=read,write", url)
        self.assertIn("state=test-state", url)

    @patch("arc_memory.auth.linear.get_token_from_env")
    @patch("arc_memory.auth.linear.get_token_from_keyring")
    @patch("arc_memory.auth.linear.get_oauth_token_from_keyring")
    def test_get_linear_token_with_fallback(self, mock_oauth, mock_keyring, mock_env):
        """Test getting a Linear token with fallback."""
        # Mock no tokens available
        mock_env.return_value = None
        mock_keyring.return_value = None
        mock_oauth.return_value = None

        # Test with allow_failure=True
        result = get_linear_token(allow_failure=True)
        self.assertIsNone(result)

        # Test with allow_failure=False
        with self.assertRaises(LinearAuthError):
            get_linear_token(allow_failure=False)

        # Test with explicit token
        result = get_linear_token(token="test-token", allow_failure=True)
        self.assertEqual(result, "test-token")

    @patch("arc_memory.auth.linear.get_token_from_env")
    @patch("arc_memory.auth.linear.get_token_from_keyring")
    @patch("arc_memory.auth.linear.get_oauth_token_from_keyring")
    def test_get_linear_token_prefer_oauth(self, mock_oauth, mock_keyring, mock_env):
        """Test that OAuth tokens are preferred over API keys."""
        # Mock an OAuth token and an API key
        mock_oauth.return_value = LinearOAuthToken(
            access_token="oauth-token",
            token_type="Bearer",
            expires_in=3600,
            scope="read,write",
            created_at=datetime.now()
        )
        mock_keyring.return_value = "api-key"
        mock_env.return_value = None

        # Test with prefer_oauth=True (default)
        result = get_linear_token()
        self.assertEqual(result, "oauth-token")

        # Test with prefer_oauth=False
        result = get_linear_token(prefer_oauth=False)
        self.assertEqual(result, "api-key")

    @patch("arc_memory.auth.linear.get_token_from_env")
    @patch("arc_memory.auth.linear.get_token_from_keyring")
    @patch("arc_memory.auth.linear.get_oauth_token_from_keyring")
    def test_get_linear_token_expired_oauth(self, mock_oauth, mock_keyring, mock_env):
        """Test that expired OAuth tokens are not used."""
        # Mock an expired OAuth token and an API key
        expired_token = LinearOAuthToken(
            access_token="expired-oauth-token",
            token_type="Bearer",
            expires_in=3600,
            scope="read,write",
            created_at=datetime.now() - timedelta(hours=2)  # 2 hours ago, so it's expired
        )
        mock_oauth.return_value = expired_token
        mock_keyring.return_value = "api-key"
        mock_env.return_value = None

        # Test with prefer_oauth=True (default)
        # Should fall back to API key since OAuth token is expired
        result = get_linear_token()
        self.assertEqual(result, "api-key")

    @patch("keyring.set_password")
    @patch("arc_memory.auth.linear.encrypt_token")
    def test_store_oauth_token_in_keyring(self, mock_encrypt, mock_set_password):
        """Test storing an OAuth token in the keyring."""
        # Mock the encryption function to return the original string
        # This allows us to test the token serialization without encryption
        mock_encrypt.side_effect = lambda x: x

        token = LinearOAuthToken(
            access_token="test-token",
            token_type="Bearer",
            expires_in=3600,
            scope="read,write",
            created_at=datetime.now()
        )

        result = store_oauth_token_in_keyring(token)

        self.assertTrue(result)
        mock_set_password.assert_called_once()
        mock_encrypt.assert_called_once()

        # Check that the token was serialized correctly
        args = mock_set_password.call_args[0]
        self.assertEqual(args[0], "arc-memory")  # service name
        self.assertEqual(args[1], "linear-oauth-token")  # username

        # Parse the JSON to check the token data
        token_data = json.loads(args[2])
        self.assertEqual(token_data["access_token"], "test-token")
        self.assertEqual(token_data["token_type"], "Bearer")
        self.assertEqual(token_data["expires_in"], 3600)
        self.assertEqual(token_data["scope"], "read,write")
        self.assertIn("created_at", token_data)


if __name__ == "__main__":
    unittest.main()
