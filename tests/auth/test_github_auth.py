"""Tests for GitHub authentication."""

import unittest
from unittest.mock import MagicMock, patch

from arc_memory.auth.default_credentials import DEFAULT_GITHUB_CLIENT_ID
from arc_memory.auth.github import get_github_token, start_device_flow, validate_client_id
from arc_memory.errors import GitHubAuthError


class TestGitHubAuth(unittest.TestCase):
    """Tests for GitHub authentication."""

    @patch("arc_memory.auth.github.requests.post")
    def test_start_device_flow(self, mock_post):
        """Test starting the device flow."""
        # Mock the response from GitHub
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "device_code": "test-device-code",
            "user_code": "TEST-CODE",
            "verification_uri": "https://github.com/login/device",
            "interval": 5,
        }
        mock_post.return_value = mock_response

        # Call the function
        device_code, verification_uri, interval = start_device_flow("test-client-id")

        # Check the results
        self.assertEqual(device_code, "test-device-code")
        self.assertEqual(verification_uri, "https://github.com/login/device")
        self.assertEqual(interval, 5)

        # Check that the request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://github.com/login/device/code")
        self.assertEqual(kwargs["json"]["client_id"], "test-client-id")
        self.assertEqual(kwargs["json"]["scope"], "repo")

    @patch("arc_memory.auth.github.requests.post")
    def test_start_device_flow_error(self, mock_post):
        """Test error handling when starting the device flow."""
        # Mock an error response
        mock_post.side_effect = Exception("Test error")

        # Call the function and check that it raises an error
        with self.assertRaises(GitHubAuthError):
            start_device_flow("test-client-id")

    def test_default_client_id(self):
        """Test that the default client ID is set."""
        # This test will fail if DEFAULT_GITHUB_CLIENT_ID is not set
        # or if it's set to the placeholder value
        self.assertIsNotNone(DEFAULT_GITHUB_CLIENT_ID)
        self.assertNotEqual(DEFAULT_GITHUB_CLIENT_ID, "")

        # This check ensures we're not using the placeholder value
        self.assertNotEqual(DEFAULT_GITHUB_CLIENT_ID, "YOUR_CLIENT_ID")


    def test_validate_client_id(self):
        """Test client ID validation."""
        # Valid client IDs
        self.assertTrue(validate_client_id("Iv1.c7a1e9e1b1e0f0e0"))
        self.assertTrue(validate_client_id("1234567890abcdef1234"))

        # Invalid client IDs
        self.assertFalse(validate_client_id(""))
        self.assertFalse(validate_client_id(None))
        self.assertFalse(validate_client_id("short"))

    @patch("arc_memory.auth.github.get_token_from_env")
    @patch("arc_memory.auth.github.get_token_from_keyring")
    def test_get_github_token_with_fallback(self, mock_keyring, mock_env):
        """Test getting a GitHub token with fallback."""
        # Mock no tokens available
        mock_env.return_value = None
        mock_keyring.return_value = None

        # Test with allow_failure=True
        result = get_github_token(allow_failure=True)
        self.assertIsNone(result)

        # Test with allow_failure=False
        with self.assertRaises(GitHubAuthError):
            get_github_token(allow_failure=False)

        # Test with explicit token
        result = get_github_token(token="test-token", allow_failure=True)
        self.assertEqual(result, "test-token")


if __name__ == "__main__":
    unittest.main()
