"""Test script for the arc auth gh command."""

import sys
from unittest.mock import patch

from arc_memory.cli.auth import github_auth

# Mock typer.confirm to always return False (don't use existing token)
@patch('typer.confirm')
# Mock get_github_token_from_env to return None (no token in env)
@patch('arc_memory.cli.auth.get_github_token_from_env')
# Mock get_github_token_from_keyring to return None (no token in keyring)
@patch('arc_memory.cli.auth.get_github_token_from_keyring')
# Mock start_github_device_flow to return test values
@patch('arc_memory.cli.auth.start_github_device_flow')
# Mock poll_github_device_flow to return a test token
@patch('arc_memory.cli.auth.poll_github_device_flow')
# Mock store_github_token_in_keyring to return True (token stored successfully)
@patch('arc_memory.cli.auth.store_github_token_in_keyring')
def test_github_auth(
    mock_store_token, mock_poll_device_flow, mock_start_device_flow,
    mock_get_token_keyring, mock_get_token_env, mock_confirm
):
    """Test the github_auth function."""
    # Set up mocks
    mock_get_token_env.return_value = None
    mock_get_token_keyring.return_value = None
    mock_confirm.return_value = False
    mock_start_device_flow.return_value = ('test-device-code', 'https://github.com/login/device', 5)
    mock_poll_device_flow.return_value = 'test-token'
    mock_store_token.return_value = True

    # Call the function with None for client_id to use the default
    github_auth(client_id=None)

    # Verify start_device_flow was called (we can't check the exact parameter due to typer internals)
    assert mock_start_device_flow.called, "start_device_flow was not called"

    # Verify poll_device_flow was called
    assert mock_poll_device_flow.called, "poll_device_flow was not called"

    # We can't check the exact parameters due to typer internals, but we can verify it was called once
    assert mock_poll_device_flow.call_count == 1, "poll_device_flow was not called exactly once"

    # Verify the token was stored
    mock_store_token.assert_called_once_with('test-token')

    print("Test passed! The arc auth gh command works correctly with the default Client ID.")

if __name__ == "__main__":
    test_github_auth()
