"""Tests for auto-refresh functionality."""

import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from arc_memory.auto_refresh.core import (
    check_refresh_needed,
    get_sources_needing_refresh,
    refresh_all_sources,
    refresh_source,
)
from arc_memory.errors import AutoRefreshError


class TestAutoRefresh(unittest.TestCase):
    """Tests for auto-refresh functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create patches for the metadata functions
        self.get_refresh_timestamp_patcher = patch("arc_memory.auto_refresh.core.get_refresh_timestamp")
        self.get_all_refresh_timestamps_patcher = patch("arc_memory.auto_refresh.core.get_all_refresh_timestamps")

        # Create a mock adapter
        self.mock_adapter = MagicMock()
        self.mock_adapter.save_refresh_timestamp = MagicMock()
        self.get_adapter_patcher = patch("arc_memory.auto_refresh.core.get_adapter", return_value=self.mock_adapter)

        # Start the patches
        self.mock_get_refresh_timestamp = self.get_refresh_timestamp_patcher.start()
        self.mock_get_all_refresh_timestamps = self.get_all_refresh_timestamps_patcher.start()
        self.mock_get_adapter = self.get_adapter_patcher.start()

    def tearDown(self):
        """Clean up test environment."""
        # Stop the patches
        self.get_refresh_timestamp_patcher.stop()
        self.get_all_refresh_timestamps_patcher.stop()
        self.get_adapter_patcher.stop()

    def test_check_refresh_needed_never_refreshed(self):
        """Test checking if a source needs refreshing when it has never been refreshed."""
        # Mock the get_refresh_timestamp function to return None
        self.mock_get_refresh_timestamp.return_value = None

        # Check if the source needs refreshing
        needs_refresh, last_refresh = check_refresh_needed("github")

        # Verify the results
        self.assertTrue(needs_refresh)
        self.assertIsNone(last_refresh)

        # Verify the mock was called correctly
        self.mock_get_refresh_timestamp.assert_called_once_with("github", None)

    def test_check_refresh_needed_recently_refreshed(self):
        """Test checking if a source needs refreshing when it was recently refreshed."""
        # Mock the get_refresh_timestamp function to return a recent timestamp
        now = datetime.now()
        self.mock_get_refresh_timestamp.return_value = now - timedelta(minutes=30)

        # Check if the source needs refreshing with a 1-hour interval
        needs_refresh, last_refresh = check_refresh_needed("github", timedelta(hours=1))

        # Verify the results
        self.assertFalse(needs_refresh)
        self.assertEqual(last_refresh, now - timedelta(minutes=30))

        # Verify the mock was called correctly
        self.mock_get_refresh_timestamp.assert_called_once_with("github", None)

    def test_check_refresh_needed_old_refresh(self):
        """Test checking if a source needs refreshing when it was refreshed a long time ago."""
        # Mock the get_refresh_timestamp function to return an old timestamp
        now = datetime.now()
        self.mock_get_refresh_timestamp.return_value = now - timedelta(hours=2)

        # Check if the source needs refreshing with a 1-hour interval
        needs_refresh, last_refresh = check_refresh_needed("github", timedelta(hours=1))

        # Verify the results
        self.assertTrue(needs_refresh)
        self.assertEqual(last_refresh, now - timedelta(hours=2))

        # Verify the mock was called correctly
        self.mock_get_refresh_timestamp.assert_called_once_with("github", None)

    def test_get_sources_needing_refresh(self):
        """Test getting a list of sources that need refreshing."""
        # Mock the check_refresh_needed function to return appropriate values
        with patch("arc_memory.auto_refresh.core.check_refresh_needed") as mock_check_refresh_needed:
            now = datetime.now()
            mock_check_refresh_needed.side_effect = [
                (True, now - timedelta(hours=2)),  # github needs refresh
                (False, now - timedelta(minutes=30)),  # linear doesn't need refresh
                (True, now - timedelta(hours=3))  # adr needs refresh
            ]

            # Get the sources that need refreshing
            sources_to_refresh = get_sources_needing_refresh(["github", "linear", "adr"], timedelta(hours=1))

            # Verify the results
            self.assertEqual(len(sources_to_refresh), 2)
            self.assertIn("github", sources_to_refresh)
            self.assertIn("adr", sources_to_refresh)
            self.assertNotIn("linear", sources_to_refresh)

            # Verify the mock was called correctly
            self.assertEqual(mock_check_refresh_needed.call_count, 3)

    def test_refresh_source(self):
        """Test refreshing a specific source."""
        # Mock the check_refresh_needed function to return True
        with patch("arc_memory.auto_refresh.core.check_refresh_needed") as mock_check_refresh_needed:
            mock_check_refresh_needed.return_value = (True, None)

            # Mock the dynamic import
            mock_module = MagicMock()
            mock_refresh_func = MagicMock(return_value=True)
            mock_module.refresh = mock_refresh_func

            with patch.dict("sys.modules", {"arc_memory.auto_refresh.sources.github": mock_module}):
                # Refresh the source
                result = refresh_source("github")

                # Verify the results
                self.assertTrue(result)

                # Verify the mocks were called correctly
                mock_check_refresh_needed.assert_called_once_with("github", None, None)
                mock_refresh_func.assert_called_once()
                self.mock_adapter.save_refresh_timestamp.assert_called_once()

    @patch("arc_memory.auto_refresh.core.refresh_source")
    def test_refresh_all_sources(self, mock_refresh_source):
        """Test refreshing all sources."""
        # Mock the get_sources_needing_refresh function to return some sources
        with patch("arc_memory.auto_refresh.core.get_sources_needing_refresh") as mock_get_sources_needing_refresh:
            mock_get_sources_needing_refresh.return_value = {
                "github": datetime.now() - timedelta(hours=2),
                "adr": datetime.now() - timedelta(hours=3)
            }

            # Mock the refresh_source function to return True
            mock_refresh_source.return_value = True

            # Refresh all sources
            results = refresh_all_sources()

            # Verify the results
            self.assertEqual(len(results), 2)
            self.assertTrue(results["github"])
            self.assertTrue(results["adr"])

            # Verify the mocks were called correctly
            mock_get_sources_needing_refresh.assert_called_once_with(None, None, None)
            self.assertEqual(mock_refresh_source.call_count, 2)

    @patch("arc_memory.auto_refresh.core.refresh_source")
    def test_refresh_all_sources_with_error(self, mock_refresh_source):
        """Test refreshing all sources when one source fails."""
        # Mock the get_sources_needing_refresh function to return some sources
        with patch("arc_memory.auto_refresh.core.get_sources_needing_refresh") as mock_get_sources_needing_refresh:
            mock_get_sources_needing_refresh.return_value = {
                "github": datetime.now() - timedelta(hours=2),
                "linear": datetime.now() - timedelta(hours=3)
            }

            # Set up the mock to raise an exception for linear
            mock_refresh_source.side_effect = [True, Exception("Test error")]

            # Refresh all sources and expect an AutoRefreshError
            with self.assertRaises(AutoRefreshError):
                refresh_all_sources()

            # Verify the mocks were called correctly
            mock_get_sources_needing_refresh.assert_called_once_with(None, None, None)
            self.assertEqual(mock_refresh_source.call_count, 2)
