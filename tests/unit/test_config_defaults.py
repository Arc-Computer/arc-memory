"""Test default configuration settings."""

import unittest

from arc_memory.config import DEFAULT_CONFIG


class TestConfigDefaults(unittest.TestCase):
    """Test default configuration settings."""

    def test_telemetry_disabled_by_default(self):
        """Test that telemetry is disabled by default."""
        self.assertIn("telemetry", DEFAULT_CONFIG)
        self.assertIn("enabled", DEFAULT_CONFIG["telemetry"])
        self.assertFalse(DEFAULT_CONFIG["telemetry"]["enabled"])
        # This test ensures that telemetry is opt-in (disabled by default)
        # as stated in the documentation


if __name__ == "__main__":
    unittest.main()
