"""Tests for the progress module."""

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from arc_memory.sdk.progress import ProgressStage, ProgressCallback, LoggingProgressCallback


class TestProgress(unittest.TestCase):
    """Tests for the progress module."""

    def test_progress_stage_enum(self):
        """Test the ProgressStage enum."""
        # Check that all expected stages are defined
        self.assertEqual(ProgressStage.INITIALIZING, "initializing")
        self.assertEqual(ProgressStage.QUERYING, "querying")
        self.assertEqual(ProgressStage.PROCESSING, "processing")
        self.assertEqual(ProgressStage.ANALYZING, "analyzing")
        self.assertEqual(ProgressStage.GENERATING, "generating")
        self.assertEqual(ProgressStage.COMPLETING, "completing")

    def test_progress_callback_base_class(self):
        """Test the ProgressCallback base class."""
        # Create an instance of ProgressCallback
        callback = ProgressCallback()

        # Call the callback
        # This should not raise an exception, even though the method is empty
        callback(
            stage=ProgressStage.INITIALIZING,
            message="Test message",
            progress=0.5,
            metadata={"key": "value"}
        )

    def test_logging_progress_callback(self):
        """Test the LoggingProgressCallback class."""
        # Mock the logger
        with patch("arc_memory.sdk.progress.logger") as mock_logger:
            # Create an instance of LoggingProgressCallback
            callback = LoggingProgressCallback()

            # Call the callback
            callback(
                stage=ProgressStage.INITIALIZING,
                message="Test message",
                progress=0.5,
                metadata={"key": "value"}
            )

            # Check that the logger was called with the expected message
            mock_logger.info.assert_called_once_with("[initializing] Test message (50%)")

            # Call the callback with different parameters
            callback(
                stage=ProgressStage.COMPLETING,
                message="Completed",
                progress=1.0
            )

            # Check that the logger was called with the expected message
            mock_logger.info.assert_called_with("[completing] Completed (100%)")


if __name__ == "__main__":
    unittest.main()
