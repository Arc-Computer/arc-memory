"""Test PostHog integration."""

import sys
import unittest
from unittest.mock import patch, MagicMock

from arc_memory.telemetry import (
    _get_posthog_client,
    track_command_usage,
    track_session_event,
    end_investigation_session,
)


class TestPostHogIntegration(unittest.TestCase):
    """Test PostHog integration."""

    @patch("posthog.Posthog")
    @patch("arc_memory.telemetry.get_config")
    def test_get_posthog_client(self, mock_get_config, mock_posthog):
        """Test getting the PostHog client."""
        # Mock the config
        mock_get_config.return_value = {
            "telemetry": {
                "enabled": True,
                "installation_id": "test-installation-id",
            }
        }

        # Mock the PostHog client
        mock_posthog_instance = MagicMock()
        mock_posthog.return_value = mock_posthog_instance

        # Mock the import
        with patch("arc_memory.telemetry._posthog_client", None):
            with patch.dict("sys.modules", {"posthog": MagicMock()}):
                with patch("posthog.Posthog", mock_posthog):
                    # Get the PostHog client
                    client = _get_posthog_client()

                    # Check that the client was initialized correctly
                    self.assertIsNotNone(client)

    @patch("arc_memory.telemetry._get_posthog_client")
    @patch("arc_memory.telemetry.get_config")
    def test_track_command_usage(self, mock_get_config, mock_get_posthog_client):
        """Test tracking command usage."""
        # Mock the config
        mock_get_config.return_value = {
            "telemetry": {
                "enabled": True,
                "installation_id": "test-installation-id",
                "current_session_id": "test-session-id",
            }
        }

        # Mock the PostHog client
        mock_posthog_client = MagicMock()
        mock_get_posthog_client.return_value = mock_posthog_client

        # Track command usage
        track_command_usage("test_command", success=True, context={"test": "value"})

        # Check that the event was captured
        mock_posthog_client.capture.assert_called_once()
        args, kwargs = mock_posthog_client.capture.call_args
        self.assertEqual(kwargs["distinct_id"], "test-installation-id")
        self.assertEqual(kwargs["event"], "command_test_command")
        self.assertEqual(kwargs["properties"]["command"], "test_command")
        self.assertEqual(kwargs["properties"]["success"], True)
        self.assertEqual(kwargs["properties"]["test"], "value")

    @patch("arc_memory.telemetry._get_posthog_client")
    @patch("arc_memory.telemetry.get_config")
    def test_track_session_event(self, mock_get_config, mock_get_posthog_client):
        """Test tracking session events."""
        # Mock the config
        mock_get_config.return_value = {
            "telemetry": {
                "enabled": True,
                "installation_id": "test-installation-id",
            }
        }

        # Mock the PostHog client
        mock_posthog_client = MagicMock()
        mock_get_posthog_client.return_value = mock_posthog_client

        # Track session event
        track_session_event("session_start", "test-session-id")

        # Check that the event was captured
        mock_posthog_client.capture.assert_called_once()
        args, kwargs = mock_posthog_client.capture.call_args
        self.assertEqual(kwargs["distinct_id"], "test-installation-id")
        self.assertEqual(kwargs["event"], "session_start")
        self.assertEqual(kwargs["properties"]["session_id"], "test-session-id")

    @patch("arc_memory.telemetry.track_session_event")
    @patch("arc_memory.telemetry.update_config")
    @patch("arc_memory.telemetry.get_config")
    def test_end_investigation_session(
        self, mock_get_config, mock_update_config, mock_track_session_event
    ):
        """Test ending an investigation session."""
        # Mock the config
        mock_get_config.return_value = {
            "telemetry": {
                "enabled": True,
                "installation_id": "test-installation-id",
                "current_session_id": "test-session-id",
            }
        }

        # End the session
        end_investigation_session()

        # Check that the session end event was tracked
        mock_track_session_event.assert_called_once_with("session_end", "test-session-id")

        # Check that the session ID was cleared
        mock_update_config.assert_called_once_with("telemetry", "current_session_id", None)


if __name__ == "__main__":
    unittest.main()
