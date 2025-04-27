"""Tests for GitHub authentication."""

import unittest
from unittest.mock import MagicMock, patch

from arc_memory.auth.default_credentials import DEFAULT_GITHUB_CLIENT_ID
from arc_memory.auth.github import start_device_flow
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
        self.assertEqual(args[0], "https://api.github.com/login/device/code")
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


if __name__ == "__main__":
    unittest.main()
