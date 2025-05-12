"""Tests for the cache module."""

import json
import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from arc_memory.sdk.cache import cache_key, cached, get_cache_dir


class TestCache(unittest.TestCase):
    """Tests for the cache module."""

    def test_get_cache_dir(self):
        """Test the get_cache_dir function."""
        with patch("arc_memory.sql.db.ensure_arc_dir") as mock_ensure_arc_dir:
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                # Set up the mock
                mock_ensure_arc_dir.return_value = Path("/path/to/arc")

                # Call the function
                result = get_cache_dir()

                # Check the result
                self.assertEqual(result, Path("/path/to/arc/cache"))

                # Check that ensure_arc_dir was called
                mock_ensure_arc_dir.assert_called_once()

                # Check that mkdir was called
                mock_mkdir.assert_called_once_with(exist_ok=True)

    def test_cache_key(self):
        """Test the cache_key function."""
        # Test with simple arguments
        key1 = cache_key("test_func", (1, "test"), {"a": 2, "b": "value"})
        self.assertIsInstance(key1, str)
        self.assertTrue(len(key1) > 0)

        # Test with Path objects
        key2 = cache_key("test_func", (Path("/path/to/file"),), {"path": Path("/another/path")})
        self.assertIsInstance(key2, str)
        self.assertTrue(len(key2) > 0)

        # Test that different arguments produce different keys
        key3 = cache_key("test_func", (1, "test"), {"a": 3, "b": "value"})
        self.assertNotEqual(key1, key3)

    def test_cached_decorator(self):
        """Test the cached decorator."""
        # Create a temporary directory for the cache
        import tempfile
        temp_dir = tempfile.mkdtemp()

        try:
            # Mock the get_cache_dir function to return our temporary directory
            with patch("arc_memory.sdk.cache.get_cache_dir") as mock_get_cache_dir:
                mock_get_cache_dir.return_value = Path(temp_dir)

                # Create a mock function to cache
                mock_func = MagicMock(return_value="test_result")
                mock_func.__name__ = "mock_func"

                # Apply the cached decorator
                cached_func = cached()(mock_func)

                # Call the function for the first time
                result1 = cached_func(1, "test", a=2)

                # Check that the function was called and the result is correct
                mock_func.assert_called_once_with(1, "test", a=2)
                self.assertEqual(result1, "test_result")

                # Reset the mock
                mock_func.reset_mock()

                # Call the function again with the same arguments
                result2 = cached_func(1, "test", a=2)

                # Check that the function was not called again and the result is correct
                mock_func.assert_not_called()
                self.assertEqual(result2, "test_result")

                # Call the function with different arguments
                result3 = cached_func(1, "test", a=3)

                # Check that the function was called and the result is correct
                mock_func.assert_called_once_with(1, "test", a=3)
                self.assertEqual(result3, "test_result")

                # Call the function with cache=False
                mock_func.reset_mock()
                result4 = cached_func(1, "test", a=2, cache=False)

                # Check that the function was called and the result is correct
                mock_func.assert_called_once_with(1, "test", a=2)
                self.assertEqual(result4, "test_result")

        finally:
            # Clean up the temporary directory
            import shutil
            shutil.rmtree(temp_dir)

    def test_cached_decorator_with_expired_cache(self):
        """Test the cached decorator with an expired cache."""
        # Create a temporary directory for the cache
        import tempfile
        temp_dir = tempfile.mkdtemp()

        try:
            # Mock the get_cache_dir function to return our temporary directory
            with patch("arc_memory.sdk.cache.get_cache_dir") as mock_get_cache_dir:
                mock_get_cache_dir.return_value = Path(temp_dir)

                # Create a mock function to cache
                mock_func = MagicMock(return_value="test_result")
                mock_func.__name__ = "mock_func"

                # Apply the cached decorator with a short TTL
                cached_func = cached(ttl=timedelta(seconds=0.1))(mock_func)

                # Call the function for the first time
                result1 = cached_func(1, "test", a=2)

                # Check that the function was called and the result is correct
                mock_func.assert_called_once_with(1, "test", a=2)
                self.assertEqual(result1, "test_result")

                # Reset the mock
                mock_func.reset_mock()

                # Wait for the cache to expire
                import time
                time.sleep(0.2)

                # Call the function again with the same arguments
                result2 = cached_func(1, "test", a=2)

                # Check that the function was called again and the result is correct
                mock_func.assert_called_once_with(1, "test", a=2)
                self.assertEqual(result2, "test_result")

        finally:
            # Clean up the temporary directory
            import shutil
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
