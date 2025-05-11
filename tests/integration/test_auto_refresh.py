"""Integration tests for auto-refresh functionality."""

import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from arc_memory.auto_refresh.core import (
    check_refresh_needed,
    get_sources_needing_refresh,
    refresh_all_sources,
    refresh_source,
)
from arc_memory.errors import AutoRefreshError
from arc_memory.sql.db import init_db


class TestAutoRefreshIntegration(unittest.TestCase):
    """Integration tests for auto-refresh functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for the test database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_graph.db"

        # Initialize the database
        init_db(self.db_path)

        # Set up environment variables to use the test database
        self.original_db_path = os.environ.get("ARC_DB_PATH")
        os.environ["ARC_DB_PATH"] = str(self.db_path)

        # Connect to the database
        from arc_memory.db import get_adapter
        self.adapter = get_adapter()
        self.adapter.connect({"db_path": str(self.db_path)})

        # Initialize the database schema
        self.adapter.init_db()

    def tearDown(self):
        """Clean up test environment."""
        # Disconnect from the database
        if hasattr(self, 'adapter') and self.adapter.is_connected():
            self.adapter.disconnect()

        # Restore the original environment variables
        if self.original_db_path:
            os.environ["ARC_DB_PATH"] = self.original_db_path
        else:
            os.environ.pop("ARC_DB_PATH", None)

        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_save_and_get_refresh_timestamp(self):
        """Test saving and retrieving refresh timestamps."""
        # Save a refresh timestamp directly using the adapter
        now = datetime.now()
        self.adapter.save_refresh_timestamp("github", now)

        # Retrieve the timestamp directly using the adapter
        timestamp = self.adapter.get_refresh_timestamp("github")

        # Verify the timestamp
        self.assertIsNotNone(timestamp)
        self.assertEqual(timestamp.isoformat(), now.isoformat())

    def test_check_refresh_needed(self):
        """Test checking if a source needs refreshing."""
        # Save a refresh timestamp from 2 hours ago
        now = datetime.now()
        two_hours_ago = now - timedelta(hours=2)
        self.adapter.save_refresh_timestamp("github", two_hours_ago)

        # Mock the get_refresh_timestamp function to use our adapter
        with patch("arc_memory.auto_refresh.core.get_refresh_timestamp") as mock_get_timestamp:
            mock_get_timestamp.return_value = two_hours_ago

            # Check if refresh is needed with a 1-hour interval
            needs_refresh, last_refresh = check_refresh_needed("github", timedelta(hours=1))

            # Verify the results
            self.assertTrue(needs_refresh)
            self.assertEqual(last_refresh, two_hours_ago)

            # Check if refresh is needed with a 3-hour interval
            needs_refresh, last_refresh = check_refresh_needed("github", timedelta(hours=3))

            # Verify the results
            self.assertFalse(needs_refresh)
            self.assertEqual(last_refresh, two_hours_ago)

    def test_get_sources_needing_refresh(self):
        """Test getting a list of sources that need refreshing."""
        # Save refresh timestamps
        now = datetime.now()
        github_ts = now - timedelta(hours=2)  # 2 hours ago
        linear_ts = now - timedelta(minutes=30)  # 30 minutes ago
        adr_ts = now - timedelta(hours=3)  # 3 hours ago

        self.adapter.save_refresh_timestamp("github", github_ts)
        self.adapter.save_refresh_timestamp("linear", linear_ts)
        self.adapter.save_refresh_timestamp("adr", adr_ts)

        # Mock the get_all_refresh_timestamps function
        with patch("arc_memory.auto_refresh.core.get_all_refresh_timestamps") as mock_get_all:
            mock_get_all.return_value = {
                "github": github_ts,
                "linear": linear_ts,
                "adr": adr_ts
            }

            # Mock the check_refresh_needed function
            with patch("arc_memory.auto_refresh.core.check_refresh_needed") as mock_check:
                mock_check.side_effect = [
                    (True, github_ts),  # github needs refresh
                    (False, linear_ts),  # linear doesn't need refresh
                    (True, adr_ts)  # adr needs refresh
                ]

                # Get sources needing refresh with a 1-hour interval
                sources_to_refresh = get_sources_needing_refresh(
                    ["github", "linear", "adr"],
                    timedelta(hours=1)
                )

                # Verify the results
                self.assertEqual(len(sources_to_refresh), 2)
                self.assertIn("github", sources_to_refresh)
                self.assertIn("adr", sources_to_refresh)
                self.assertNotIn("linear", sources_to_refresh)

    @patch("arc_memory.auto_refresh.sources.github.refresh")
    def test_refresh_source(self, mock_github_refresh):
        """Test refreshing a specific source."""
        # Mock the GitHub refresh function
        mock_github_refresh.return_value = True

        # Save a refresh timestamp from 2 hours ago
        now = datetime.now()
        two_hours_ago = now - timedelta(hours=2)
        self.adapter.save_refresh_timestamp("github", two_hours_ago)

        # Mock the check_refresh_needed function
        with patch("arc_memory.auto_refresh.core.check_refresh_needed") as mock_check:
            mock_check.return_value = (True, two_hours_ago)

            # Mock the adapter's save_refresh_timestamp method
            with patch.object(self.adapter.__class__, "save_refresh_timestamp") as mock_save:
                # Refresh the source
                result = refresh_source("github", min_interval=timedelta(hours=1))

                # Verify the results
                self.assertTrue(result)
                mock_github_refresh.assert_called_once()
                mock_save.assert_called_once()

    @patch("arc_memory.auto_refresh.sources.github.refresh")
    @patch("arc_memory.auto_refresh.sources.linear.refresh")
    def test_refresh_all_sources(self, mock_linear_refresh, mock_github_refresh):
        """Test refreshing all sources."""
        # Mock the refresh functions
        mock_github_refresh.return_value = True
        mock_linear_refresh.return_value = True

        # Save refresh timestamps
        now = datetime.now()
        github_ts = now - timedelta(hours=2)  # 2 hours ago
        linear_ts = now - timedelta(hours=3)  # 3 hours ago

        self.adapter.save_refresh_timestamp("github", github_ts)
        self.adapter.save_refresh_timestamp("linear", linear_ts)

        # Mock the get_sources_needing_refresh function
        with patch("arc_memory.auto_refresh.core.get_sources_needing_refresh") as mock_get_sources:
            mock_get_sources.return_value = {
                "github": github_ts,
                "linear": linear_ts
            }

            # Mock the refresh_source function
            with patch("arc_memory.auto_refresh.core.refresh_source") as mock_refresh:
                mock_refresh.side_effect = [True, True]

                # Refresh all sources
                results = refresh_all_sources(
                    ["github", "linear"],
                    force=False,
                    min_interval=timedelta(hours=1)
                )

                # Verify the results
                self.assertEqual(len(results), 2)
                self.assertTrue(results["github"])
                self.assertTrue(results["linear"])
                self.assertEqual(mock_refresh.call_count, 2)

    @patch("arc_memory.auto_refresh.sources.github.refresh")
    def test_refresh_source_not_needed(self, mock_github_refresh):
        """Test refreshing a source that doesn't need refreshing."""
        # Mock the GitHub refresh function
        mock_github_refresh.return_value = True

        # Save a recent refresh timestamp
        now = datetime.now()
        recent_ts = now - timedelta(minutes=30)
        self.adapter.save_refresh_timestamp("github", recent_ts)

        # Mock the check_refresh_needed function
        with patch("arc_memory.auto_refresh.core.check_refresh_needed") as mock_check:
            mock_check.return_value = (False, recent_ts)

            # Refresh the source
            result = refresh_source("github", min_interval=timedelta(hours=1))

            # Verify the results
            self.assertFalse(result)
            mock_github_refresh.assert_not_called()

    @patch("arc_memory.auto_refresh.sources.github.refresh")
    def test_force_refresh(self, mock_github_refresh):
        """Test forcing a refresh even if not needed."""
        # Mock the GitHub refresh function
        mock_github_refresh.return_value = True

        # Save a recent refresh timestamp
        now = datetime.now()
        recent_ts = now - timedelta(minutes=30)
        self.adapter.save_refresh_timestamp("github", recent_ts)

        # Mock the adapter's save_refresh_timestamp method
        with patch.object(self.adapter.__class__, "save_refresh_timestamp") as mock_save:
            # Force refresh the source
            result = refresh_source("github", force=True, min_interval=timedelta(hours=1))

            # Verify the results
            self.assertTrue(result)
            mock_github_refresh.assert_called_once()
            mock_save.assert_called_once()

    @patch("arc_memory.auto_refresh.sources.github.refresh")
    def test_refresh_error_handling(self, mock_github_refresh):
        """Test error handling during refresh."""
        # Mock the GitHub refresh function to raise an exception
        mock_github_refresh.side_effect = Exception("Test error")

        # Save a refresh timestamp from 2 hours ago
        now = datetime.now()
        two_hours_ago = now - timedelta(hours=2)
        self.adapter.save_refresh_timestamp("github", two_hours_ago)

        # Mock the check_refresh_needed function
        with patch("arc_memory.auto_refresh.core.check_refresh_needed") as mock_check:
            mock_check.return_value = (True, two_hours_ago)

            # Refresh the source and expect an AutoRefreshError
            with self.assertRaises(AutoRefreshError):
                refresh_source("github", min_interval=timedelta(hours=1))

            # Verify the timestamp was not updated (we can't easily check this in the mock setup)
            # Instead, we verify that the mock_github_refresh was called
            mock_github_refresh.assert_called_once()
