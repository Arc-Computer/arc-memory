"""Tests for the trace history functionality."""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from arc_memory.schema.models import Node, NodeType
from arc_memory.trace import (
    get_commit_for_line,
    trace_history,
    get_node_by_id,
    get_connected_nodes,
    get_nodes_by_edge,
    format_trace_results,
    trace_history_for_file_line,
)


class TestTraceHistory(unittest.TestCase):
    """Test the trace history functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for the test repository
        self.repo_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.repo_dir.name)
        
        # Create a temporary SQLite database
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.conn = sqlite3.connect(self.db_path)
        
        # Create the necessary tables
        self.conn.execute("""
            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                type TEXT,
                title TEXT,
                body TEXT,
                extra TEXT
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE edges (
                src TEXT,
                dst TEXT,
                rel TEXT,
                PRIMARY KEY (src, dst, rel)
            )
        """)
        
        # Insert test data
        self.insert_test_data()
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.repo_dir.cleanup()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def insert_test_data(self):
        """Insert test data into the database."""
        # Insert nodes
        nodes = [
            ("commit:abc123", "commit", "Fix bug in authentication", "Detailed commit message", "{}"),
            ("pr:42", "pr", "PR #42: Fix authentication bug", "PR description", "{}"),
            ("issue:123", "issue", "Issue #123: Authentication fails", "Issue description", "{}"),
            ("adr:001", "adr", "ADR-001: Authentication Strategy", "ADR content", "{}"),
        ]
        
        self.conn.executemany(
            "INSERT INTO nodes (id, type, title, body, extra) VALUES (?, ?, ?, ?, ?)",
            nodes
        )
        
        # Insert edges
        edges = [
            ("commit:abc123", "pr:42", "MERGES"),
            ("pr:42", "issue:123", "MENTIONS"),
            ("adr:001", "issue:123", "DECIDES"),
        ]
        
        self.conn.executemany(
            "INSERT INTO edges (src, dst, rel) VALUES (?, ?, ?)",
            edges
        )
        
        self.conn.commit()
    
    @patch("subprocess.run")
    def test_get_commit_for_line(self, mock_run):
        """Test getting a commit for a specific line."""
        # Mock the subprocess.run call
        mock_process = MagicMock()
        mock_process.stdout = "abc123 original_line 1 1\nauthor John Doe\n"
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Call the function
        commit_id = get_commit_for_line(self.repo_path, "test_file.py", 10)
        
        # Check the result
        self.assertEqual(commit_id, "abc123")
        
        # Verify the subprocess call
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(kwargs["check"], True)
        self.assertEqual(args[0][0], "git")
        self.assertEqual(args[0][1], "-C")
        self.assertEqual(args[0][3], "blame")
    
    def test_get_node_by_id(self):
        """Test getting a node by ID."""
        # Get a node that exists
        node = get_node_by_id(self.conn, "commit:abc123")
        
        # Check the result
        self.assertIsNotNone(node)
        self.assertEqual(node.id, "commit:abc123")
        self.assertEqual(node.type, "commit")
        self.assertEqual(node.title, "Fix bug in authentication")
        
        # Get a node that doesn't exist
        node = get_node_by_id(self.conn, "nonexistent")
        
        # Check the result
        self.assertIsNone(node)
    
    def test_get_connected_nodes(self):
        """Test getting connected nodes."""
        # Test commit -> PR
        nodes = get_connected_nodes(self.conn, "commit:abc123", 0)
        self.assertEqual(nodes, ["pr:42"])
        
        # Test PR -> Issue
        nodes = get_connected_nodes(self.conn, "pr:42", 1)
        self.assertEqual(nodes, ["issue:123"])
        
        # Test Issue -> ADR (inbound)
        nodes = get_connected_nodes(self.conn, "issue:123", 1)
        self.assertEqual(nodes, ["adr:001"])
    
    def test_get_nodes_by_edge(self):
        """Test getting nodes by edge type."""
        # Test outbound edge
        nodes = get_nodes_by_edge(self.conn, "commit:abc123", "MERGES", True)
        self.assertEqual(nodes, ["pr:42"])
        
        # Test inbound edge
        nodes = get_nodes_by_edge(self.conn, "issue:123", "DECIDES", False)
        self.assertEqual(nodes, ["adr:001"])
    
    def test_format_trace_results(self):
        """Test formatting trace results."""
        # Create test nodes
        nodes = [
            Node(id="commit:abc123", type="commit", title="Fix bug", ts=None),
            Node(id="pr:42", type="pr", title="PR #42", ts=None),
            Node(id="issue:123", type="issue", title="Issue #123", ts=None),
        ]
        
        # Format the results
        results = format_trace_results(nodes)
        
        # Check the results
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["id"], "commit:abc123")
        self.assertEqual(results[1]["id"], "pr:42")
        self.assertEqual(results[2]["id"], "issue:123")
    
    @patch("arc_memory.trace.get_commit_for_line")
    @patch("arc_memory.trace.trace_history")
    def test_trace_history_for_file_line(self, mock_trace_history, mock_get_commit):
        """Test tracing history for a file line."""
        # Mock the get_commit_for_line function
        mock_get_commit.return_value = "abc123"
        
        # Mock the trace_history function
        mock_nodes = [
            Node(id="commit:abc123", type="commit", title="Fix bug", ts=None),
            Node(id="pr:42", type="pr", title="PR #42", ts=None),
            Node(id="issue:123", type="issue", title="Issue #123", ts=None),
        ]
        mock_trace_history.return_value = mock_nodes
        
        # Call the function
        results = trace_history_for_file_line(
            self.repo_path,
            Path(self.db_path),
            "test_file.py",
            10
        )
        
        # Check the results
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["id"], "commit:abc123")
        self.assertEqual(results[1]["id"], "pr:42")
        self.assertEqual(results[2]["id"], "issue:123")
        
        # Verify the function calls
        mock_get_commit.assert_called_once_with(self.repo_path, "test_file.py", 10)
        mock_trace_history.assert_called_once_with(
            Path(self.db_path),
            "abc123",
            max_hops=2,
            max_results=3
        )
    
    @patch("arc_memory.trace.get_connection")
    @patch("arc_memory.trace.get_node_by_id")
    @patch("arc_memory.trace.get_connected_nodes")
    def test_trace_history(self, mock_connected, mock_get_node, mock_get_conn):
        """Test the trace_history function."""
        # Mock the get_connection function
        mock_get_conn.return_value = self.conn
        
        # Mock the get_node_by_id function
        def mock_get_node_side_effect(conn, node_id):
            if node_id == "commit:abc123":
                return Node(id="commit:abc123", type="commit", title="Fix bug", ts=None)
            elif node_id == "pr:42":
                return Node(id="pr:42", type="pr", title="PR #42", ts=None)
            elif node_id == "issue:123":
                return Node(id="issue:123", type="issue", title="Issue #123", ts=None)
            return None
        
        mock_get_node.side_effect = mock_get_node_side_effect
        
        # Mock the get_connected_nodes function
        def mock_connected_side_effect(conn, node_id, hop_count):
            if node_id == "commit:abc123" and hop_count == 0:
                return ["pr:42"]
            elif node_id == "pr:42" and hop_count == 1:
                return ["issue:123"]
            return []
        
        mock_connected.side_effect = mock_connected_side_effect
        
        # Call the function
        results = trace_history(Path(self.db_path), "abc123", max_hops=2, max_results=3)
        
        # Check the results
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].id, "commit:abc123")
        self.assertEqual(results[1].id, "pr:42")
        self.assertEqual(results[2].id, "issue:123")


if __name__ == "__main__":
    unittest.main()
