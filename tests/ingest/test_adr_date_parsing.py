"""Tests for ADR date parsing."""

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from arc_memory.ingest.adr import parse_adr_date


class TestADRDateParsing(unittest.TestCase):
    """Tests for ADR date parsing."""

    def setUp(self):
        """Set up test environment."""
        self.test_file = Path("test_adr.md")

    @patch("arc_memory.ingest.adr.get_logger")
    def test_parse_none_date(self, mock_get_logger):
        """Test parsing None date."""
        mock_logger = mock_get_logger.return_value

        result = parse_adr_date(None, self.test_file)

        self.assertIsNone(result)
        mock_logger.warning.assert_called_once()
        self.assertIn("Missing date", mock_logger.warning.call_args[0][0])

    @patch("arc_memory.ingest.adr.get_logger")
    def test_parse_datetime_object(self, mock_get_logger):
        """Test parsing datetime object."""
        mock_logger = mock_get_logger.return_value

        dt = datetime(2023, 11, 15, 14, 30, 0)
        result = parse_adr_date(dt, self.test_file)

        self.assertEqual(result, dt)
        mock_logger.warning.assert_not_called()

    @patch("arc_memory.ingest.adr.get_logger")
    def test_parse_non_string_non_date(self, mock_get_logger):
        """Test parsing non-string, non-date value."""
        mock_logger = mock_get_logger.return_value

        result = parse_adr_date(123, self.test_file)

        self.assertIsNone(result)
        # With our new implementation, we try to convert to string first
        # and then parse it, so the error message is different
        mock_logger.warning.assert_called_once()
        self.assertIn("Could not parse date", mock_logger.warning.call_args[0][0])

    @patch("arc_memory.ingest.adr.get_logger")
    def test_parse_iso_date(self, mock_get_logger):
        """Test parsing ISO format date."""
        mock_logger = mock_get_logger.return_value

        result = parse_adr_date("2023-11-15", self.test_file)

        self.assertEqual(result, datetime(2023, 11, 15))
        mock_logger.warning.assert_not_called()

    @patch("arc_memory.ingest.adr.get_logger")
    def test_parse_iso_datetime(self, mock_get_logger):
        """Test parsing ISO format datetime."""
        mock_logger = mock_get_logger.return_value

        result = parse_adr_date("2023-11-15T14:30:00", self.test_file)

        self.assertEqual(result, datetime(2023, 11, 15, 14, 30, 0))
        mock_logger.warning.assert_not_called()

    @patch("arc_memory.ingest.adr.get_logger")
    def test_parse_slash_date(self, mock_get_logger):
        """Test parsing slash format date."""
        mock_logger = mock_get_logger.return_value

        result = parse_adr_date("2023/11/15", self.test_file)

        self.assertEqual(result, datetime(2023, 11, 15))
        mock_logger.warning.assert_not_called()

    @patch("arc_memory.ingest.adr.get_logger")
    def test_parse_european_date(self, mock_get_logger):
        """Test parsing European format date."""
        mock_logger = mock_get_logger.return_value

        result = parse_adr_date("15-11-2023", self.test_file)

        self.assertEqual(result, datetime(2023, 11, 15))
        mock_logger.warning.assert_not_called()

    @patch("arc_memory.ingest.adr.get_logger")
    def test_parse_month_name_date(self, mock_get_logger):
        """Test parsing month name format date."""
        mock_logger = mock_get_logger.return_value

        result = parse_adr_date("November 15, 2023", self.test_file)

        self.assertEqual(result, datetime(2023, 11, 15))
        mock_logger.warning.assert_not_called()

    @patch("arc_memory.ingest.adr.get_logger")
    def test_parse_invalid_date(self, mock_get_logger):
        """Test parsing invalid date."""
        mock_logger = mock_get_logger.return_value

        result = parse_adr_date("not a date", self.test_file)

        self.assertIsNone(result)
        mock_logger.warning.assert_called_once()
        self.assertIn("Could not parse date", mock_logger.warning.call_args[0][0])
        self.assertIn("Supported date formats", mock_logger.warning.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
