"""Tests for temporal utilities."""

import unittest
from datetime import datetime, timezone

from arc_memory.schema.models import Node, NodeType, CommitNode, PRNode, IssueNode, FileNode
from arc_memory.utils.temporal import normalize_timestamp, parse_timestamp, get_timestamp_str, compare_timestamps


class TestTemporalUtils(unittest.TestCase):
    """Tests for temporal utilities."""

    def test_parse_timestamp(self):
        """Test parsing timestamps."""
        # Test parsing datetime object
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(parse_timestamp(dt), dt)

        # Test parsing ISO format string
        iso_str = "2023-01-01T12:00:00"
        expected = datetime.fromisoformat(iso_str)
        self.assertEqual(parse_timestamp(iso_str), expected)

        # Test parsing ISO format string with Z
        iso_str_z = "2023-01-01T12:00:00Z"
        expected_z = datetime.fromisoformat("2023-01-01T12:00:00+00:00")
        self.assertEqual(parse_timestamp(iso_str_z), expected_z)

        # Test parsing invalid string
        self.assertIsNone(parse_timestamp("not a timestamp"))

        # Test parsing None
        self.assertIsNone(parse_timestamp(None))

    def test_get_timestamp_str(self):
        """Test converting timestamps to strings."""
        # Test converting datetime object
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(get_timestamp_str(dt), dt.isoformat())

        # Test converting ISO format string
        iso_str = "2023-01-01T12:00:00"
        expected = datetime.fromisoformat(iso_str).isoformat()
        self.assertEqual(get_timestamp_str(iso_str), expected)

        # Test converting None
        self.assertIsNone(get_timestamp_str(None))

    def test_compare_timestamps(self):
        """Test comparing timestamps."""
        # Test comparing datetime objects
        dt1 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(compare_timestamps(dt1, dt2), -1)
        self.assertEqual(compare_timestamps(dt2, dt1), 1)
        self.assertEqual(compare_timestamps(dt1, dt1), 0)

        # Test comparing ISO format strings
        iso_str1 = "2023-01-01T12:00:00"
        iso_str2 = "2023-01-02T12:00:00"
        self.assertEqual(compare_timestamps(iso_str1, iso_str2), -1)
        self.assertEqual(compare_timestamps(iso_str2, iso_str1), 1)
        self.assertEqual(compare_timestamps(iso_str1, iso_str1), 0)

        # Test comparing None values
        self.assertEqual(compare_timestamps(None, None), 0)
        self.assertEqual(compare_timestamps(None, dt1), -1)
        self.assertEqual(compare_timestamps(dt1, None), 1)

    def test_normalize_timestamp_base_ts(self):
        """Test normalizing timestamps using the base ts field."""
        # Test with base ts field
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        node = Node(id="test", type=NodeType.COMMIT, ts=dt)
        self.assertEqual(normalize_timestamp(node), dt)

    def test_normalize_timestamp_commit_node(self):
        """Test normalizing timestamps for CommitNode."""
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        node = CommitNode(
            id="commit:123",
            type=NodeType.COMMIT,
            ts=dt,
            author="test",
            files=["file1", "file2"],
            sha="123",
        )
        self.assertEqual(normalize_timestamp(node), dt)

    def test_normalize_timestamp_pr_node(self):
        """Test normalizing timestamps for PRNode."""
        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        merged_at = datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        # Test with ts field
        node = PRNode(
            id="pr:123",
            type=NodeType.PR,
            ts=created_at,
            number=123,
            state="merged",
            merged_at=merged_at,
            url="https://example.com",
        )
        self.assertEqual(normalize_timestamp(node), created_at)
        
        # Test with created_at in extra
        node = PRNode(
            id="pr:123",
            type=NodeType.PR,
            number=123,
            state="merged",
            merged_at=merged_at,
            url="https://example.com",
            extra={"created_at": created_at.isoformat()},
        )
        self.assertEqual(normalize_timestamp(node), created_at)
        
        # Test with merged_at but no ts or created_at
        node = PRNode(
            id="pr:123",
            type=NodeType.PR,
            number=123,
            state="merged",
            merged_at=merged_at,
            url="https://example.com",
        )
        self.assertEqual(normalize_timestamp(node), merged_at)

    def test_normalize_timestamp_issue_node(self):
        """Test normalizing timestamps for IssueNode."""
        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        closed_at = datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        
        # Test with ts field
        node = IssueNode(
            id="issue:123",
            type=NodeType.ISSUE,
            ts=created_at,
            number=123,
            state="closed",
            closed_at=closed_at,
            url="https://example.com",
        )
        self.assertEqual(normalize_timestamp(node), created_at)
        
        # Test with created_at in extra
        node = IssueNode(
            id="issue:123",
            type=NodeType.ISSUE,
            number=123,
            state="closed",
            closed_at=closed_at,
            url="https://example.com",
            extra={"created_at": created_at.isoformat()},
        )
        self.assertEqual(normalize_timestamp(node), created_at)

    def test_normalize_timestamp_file_node(self):
        """Test normalizing timestamps for FileNode."""
        last_modified = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Test with ts field
        node = FileNode(
            id="file:test.py",
            type=NodeType.FILE,
            ts=last_modified,
            path="test.py",
        )
        self.assertEqual(normalize_timestamp(node), last_modified)
        
        # Test with last_modified field
        node = FileNode(
            id="file:test.py",
            type=NodeType.FILE,
            path="test.py",
            last_modified=last_modified,
        )
        self.assertEqual(normalize_timestamp(node), last_modified)

    def test_normalize_timestamp_extra_fields(self):
        """Test normalizing timestamps from extra fields."""
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Test with timestamp in extra
        node = Node(
            id="test",
            type=NodeType.CONCEPT,
            extra={"timestamp": dt.isoformat()},
        )
        self.assertEqual(normalize_timestamp(node), dt)
        
        # Test with created_at in extra
        node = Node(
            id="test",
            type=NodeType.CONCEPT,
            extra={"created_at": dt.isoformat()},
        )
        self.assertEqual(normalize_timestamp(node), dt)
        
        # Test with updated_at in extra
        node = Node(
            id="test",
            type=NodeType.CONCEPT,
            extra={"updated_at": dt.isoformat()},
        )
        self.assertEqual(normalize_timestamp(node), dt)
        
        # Test with date in extra
        node = Node(
            id="test",
            type=NodeType.CONCEPT,
            extra={"date": dt.isoformat()},
        )
        self.assertEqual(normalize_timestamp(node), dt)

    def test_normalize_timestamp_no_timestamp(self):
        """Test normalizing timestamps when no timestamp is available."""
        # Test with no timestamp
        node = Node(
            id="test",
            type=NodeType.CONCEPT,
        )
        self.assertIsNone(normalize_timestamp(node))


if __name__ == "__main__":
    unittest.main()
