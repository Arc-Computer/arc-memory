"""Tests for database metadata utilities."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from arc_memory.db import get_adapter
from arc_memory.db.metadata import (
    get_all_metadata,
    get_all_refresh_timestamps,
    get_metadata,
    get_refresh_timestamp,
    save_metadata,
    save_refresh_timestamp,
)
from arc_memory.db.sqlite_adapter import SQLiteAdapter
from arc_memory.errors import DatabaseError


class TestDatabaseMetadata(unittest.TestCase):
    """Tests for database metadata utilities."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test databases
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        # Create a SQLite adapter
        self.adapter = SQLiteAdapter()
        self.adapter.connect({"db_path": self.db_path, "check_exists": False})
        self.adapter.init_db()

        # Mock the get_adapter function to return our test adapter
        self.patcher = patch("arc_memory.db.metadata.get_adapter")
        self.mock_get_adapter = self.patcher.start()
        self.mock_get_adapter.return_value = self.adapter

    def tearDown(self):
        """Clean up test environment."""
        self.patcher.stop()
        if self.adapter.is_connected():
            self.adapter.disconnect()
        self.temp_dir.cleanup()

    def test_save_get_refresh_timestamp(self):
        """Test saving and retrieving refresh timestamps."""
        # Save a refresh timestamp
        now = datetime.now()
        save_refresh_timestamp("github", now)

        # Retrieve the timestamp
        timestamp = get_refresh_timestamp("github")
        self.assertEqual(timestamp.isoformat(), now.isoformat())

        # Test non-existent source
        timestamp = get_refresh_timestamp("non_existent_source")
        self.assertIsNone(timestamp)

    def test_get_all_refresh_timestamps(self):
        """Test retrieving all refresh timestamps."""
        # Save multiple refresh timestamps
        now = datetime.now()
        later = datetime.now()
        save_refresh_timestamp("github", now)
        save_refresh_timestamp("linear", later)

        # Mock the adapter's get_all_refresh_timestamps method
        self.adapter.get_all_refresh_timestamps = MagicMock(return_value={
            "github": now,
            "linear": later
        })

        # Retrieve all timestamps
        timestamps = get_all_refresh_timestamps()
        self.assertEqual(len(timestamps), 2)
        self.assertIn("github", timestamps)
        self.assertIn("linear", timestamps)
        self.assertEqual(timestamps["github"].isoformat(), now.isoformat())
        self.assertEqual(timestamps["linear"].isoformat(), later.isoformat())

        # Verify that the adapter's method was called
        self.adapter.get_all_refresh_timestamps.assert_called_once()

    def test_save_get_metadata(self):
        """Test saving and retrieving metadata."""
        # Save metadata
        save_metadata("test_key", "test_value")

        # Retrieve metadata
        value = get_metadata("test_key")
        self.assertEqual(value, "test_value")

        # Test default value for non-existent key
        value = get_metadata("non_existent_key", "default_value")
        self.assertEqual(value, "default_value")

    def test_get_all_metadata(self):
        """Test retrieving all metadata."""
        # Save multiple metadata items
        save_metadata("test_key1", "test_value1")
        save_metadata("test_key2", "test_value2")

        # Retrieve all metadata
        metadata = get_all_metadata()
        self.assertIn("test_key1", metadata)
        self.assertIn("test_key2", metadata)
        self.assertEqual(metadata["test_key1"], "test_value1")
        self.assertEqual(metadata["test_key2"], "test_value2")

    def test_error_handling(self):
        """Test error handling in metadata utilities."""
        # Mock the adapter to raise an exception
        self.adapter.save_refresh_timestamp = MagicMock(side_effect=Exception("Test error"))

        # Test that the utility function properly handles the exception
        with self.assertRaises(DatabaseError):
            save_refresh_timestamp("github", datetime.now())

        # Mock the adapter to raise an exception
        self.adapter.get_refresh_timestamp = MagicMock(side_effect=Exception("Test error"))

        # Test that the utility function properly handles the exception
        with self.assertRaises(DatabaseError):
            get_refresh_timestamp("github")

        # Mock the adapter to raise an exception
        self.adapter.save_metadata = MagicMock(side_effect=Exception("Test error"))

        # Test that the utility function properly handles the exception
        with self.assertRaises(DatabaseError):
            save_metadata("test_key", "test_value")

        # Mock the adapter to raise an exception
        self.adapter.get_metadata = MagicMock(side_effect=Exception("Test error"))

        # Test that the utility function properly handles the exception
        with self.assertRaises(DatabaseError):
            get_metadata("test_key")

        # Mock the adapter to raise an exception
        self.adapter.get_all_metadata = MagicMock(side_effect=Exception("Test error"))

        # Test that the utility function properly handles the exception
        with self.assertRaises(DatabaseError):
            get_all_metadata()

    def test_adapter_type_parameter(self):
        """Test the adapter_type parameter in metadata utilities."""
        # Create a mock adapter
        mock_adapter = MagicMock()
        mock_adapter.get_refresh_timestamp.return_value = datetime.now()
        mock_adapter.get_metadata.return_value = "test_value"
        mock_adapter.get_all_metadata.return_value = {"test_key": "test_value"}
        mock_adapter.get_name.return_value = "mock"

        # Update the mock get_adapter function to return our mock adapter when called with "mock"
        self.mock_get_adapter.side_effect = lambda adapter_type: mock_adapter if adapter_type == "mock" else self.adapter

        # Test that the adapter_type parameter is passed to get_adapter
        save_refresh_timestamp("github", datetime.now(), adapter_type="mock")
        mock_adapter.save_refresh_timestamp.assert_called_once()

        get_refresh_timestamp("github", adapter_type="mock")
        mock_adapter.get_refresh_timestamp.assert_called_once()

        save_metadata("test_key", "test_value", adapter_type="mock")
        mock_adapter.save_metadata.assert_called_once()

        get_metadata("test_key", adapter_type="mock")
        mock_adapter.get_metadata.assert_called_once()

        get_all_metadata(adapter_type="mock")
        mock_adapter.get_all_metadata.assert_called_once()
