"""Temporal utilities for Arc Memory.

This module provides utilities for handling temporal data in the knowledge graph,
including timestamp normalization and parsing functions.
"""

from datetime import datetime
from typing import Any, Optional, Union

from arc_memory.schema.models import Node, NodeType


def normalize_timestamp(node: Node) -> Optional[datetime]:
    """Extract and normalize the primary timestamp from a node.

    This function handles different node types and their timestamp fields.

    Args:
        node: The node to extract the timestamp from

    Returns:
        The normalized timestamp or None if no timestamp is available
    """
    # Use the base ts field if available
    if node.ts:
        return node.ts

    # Handle specialized node types
    if node.type == NodeType.COMMIT:
        # CommitNode timestamps are in the ts field
        return node.ts
    elif node.type == NodeType.PR:
        # PRNode - use created_at or merged_at
        if hasattr(node, 'extra') and node.extra:
            if 'created_at' in node.extra:
                return parse_timestamp(node.extra['created_at'])

        # If no created_at in extra, try merged_at
        if hasattr(node, 'merged_at') and node.merged_at:
            return node.merged_at
    elif node.type == NodeType.ISSUE:
        # IssueNode - use created_at
        if hasattr(node, 'extra') and node.extra:
            if 'created_at' in node.extra:
                return parse_timestamp(node.extra['created_at'])
    elif node.type == NodeType.FILE:
        # FileNode - use last_modified
        if hasattr(node, 'last_modified') and node.last_modified:
            return node.last_modified

    # Check common fields in extra
    if hasattr(node, 'extra') and node.extra:
        for key in ['timestamp', 'created_at', 'updated_at', 'date']:
            if key in node.extra and node.extra[key]:
                return parse_timestamp(node.extra[key])

    return None


def parse_timestamp(timestamp_value: Any) -> Optional[datetime]:
    """Parse a timestamp value into a datetime object.

    Args:
        timestamp_value: The timestamp value to parse (string, datetime, etc.)

    Returns:
        The parsed datetime or None if parsing fails
    """
    if isinstance(timestamp_value, datetime):
        return timestamp_value
    elif isinstance(timestamp_value, str):
        try:
            # Handle ISO format with Z
            if 'Z' in timestamp_value:
                return datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
            return datetime.fromisoformat(timestamp_value)
        except ValueError:
            pass

    return None


def get_timestamp_str(timestamp: Optional[Union[datetime, str]]) -> Optional[str]:
    """Convert a timestamp to an ISO-formatted string.

    Args:
        timestamp: The timestamp to convert (datetime or string)

    Returns:
        ISO-formatted string or None if conversion fails
    """
    if timestamp is None:
        return None

    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    elif isinstance(timestamp, str):
        try:
            dt = parse_timestamp(timestamp)
            if dt:
                return dt.isoformat()
            return timestamp
        except ValueError:
            return timestamp

    return None


def compare_timestamps(ts1: Optional[Union[datetime, str]],
                      ts2: Optional[Union[datetime, str]]) -> int:
    """Compare two timestamps.

    Args:
        ts1: First timestamp
        ts2: Second timestamp

    Returns:
        -1 if ts1 < ts2, 0 if ts1 == ts2, 1 if ts1 > ts2
    """
    # Parse timestamps
    dt1 = parse_timestamp(ts1) if ts1 is not None else None
    dt2 = parse_timestamp(ts2) if ts2 is not None else None

    # Handle None values
    if dt1 is None and dt2 is None:
        return 0
    elif dt1 is None:
        return -1
    elif dt2 is None:
        return 1

    # Compare datetimes
    if dt1 < dt2:
        return -1
    elif dt1 > dt2:
        return 1
    else:
        return 0
