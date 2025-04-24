"""Comprehensive integration tests for the trace history functionality."""

import os
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel
from arc_memory.sql.db import get_connection, init_db
from arc_memory.trace import (
    get_commit_for_line,
    trace_history,
    trace_history_for_file_line,
)


class TestTraceHistoryComprehensive(unittest.TestCase):
    """Comprehensive integration tests for the trace history functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are used for all tests."""
        # Create a temporary directory for the test repository
        cls.repo_dir = tempfile.TemporaryDirectory()
        cls.repo_path = Path(cls.repo_dir.name)

        # Initialize a Git repository
        subprocess.run(["git", "init", cls.repo_path], check=True)

        # Configure Git
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=cls.repo_path,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=cls.repo_path,
            check=True
        )

        # Create a test file
        cls.test_file = cls.repo_path / "test_file.py"
        with open(cls.test_file, "w") as f:
            f.write("# Test file\n")
            f.write("def hello():\n")
            f.write("    return 'Hello, World!'\n")

        # Commit the file
        subprocess.run(
            ["git", "add", "test_file.py"],
            cwd=cls.repo_path,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=cls.repo_path,
            check=True
        )

        # Get the commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cls.repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        cls.commit_hash_1 = result.stdout.strip()

        # Modify the file
        with open(cls.test_file, "a") as f:
            f.write("\ndef goodbye():\n")
            f.write("    return 'Goodbye, World!'\n")

        # Commit the changes
        subprocess.run(
            ["git", "add", "test_file.py"],
            cwd=cls.repo_path,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add goodbye function"],
            cwd=cls.repo_path,
            check=True
        )

        # Get the second commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cls.repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        cls.commit_hash_2 = result.stdout.strip()

        # Create a complex graph database
        cls.db_path = cls.repo_path / "test.db"
        cls.conn = init_db(cls.db_path)

        # Insert test data
        cls.insert_test_data(cls.conn, cls.commit_hash_1, cls.commit_hash_2)

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        cls.conn.close()
        cls.repo_dir.cleanup()

    @classmethod
    def insert_test_data(cls, conn, commit_hash_1, commit_hash_2):
        """Insert test data into the database."""
        # Create timestamps for extra data
        timestamp_1 = datetime(2023, 4, 1, 10, 0, 0).isoformat()
        timestamp_2 = datetime(2023, 4, 2, 11, 0, 0).isoformat()
        timestamp_3 = datetime(2023, 4, 3, 12, 0, 0).isoformat()
        timestamp_4 = datetime(2023, 4, 4, 13, 0, 0).isoformat()
        timestamp_5 = datetime(2023, 4, 5, 14, 0, 0).isoformat()

        # Insert nodes
        nodes = [
            # Commits
            (f"commit:{commit_hash_1}", NodeType.COMMIT, "Initial commit",
             "Initial commit message",
             '{"author": "Test User", "sha": "' + commit_hash_1 + '", "ts": "' + timestamp_1 + '"}'),

            (f"commit:{commit_hash_2}", NodeType.COMMIT, "Add goodbye function",
             "Add goodbye function message",
             '{"author": "Test User", "sha": "' + commit_hash_2 + '", "ts": "' + timestamp_2 + '"}'),

            # Files
            ("file:test_file.py", NodeType.FILE, "test_file.py",
             "File content",
             '{"path": "test_file.py", "language": "python", "ts": "' + timestamp_1 + '"}'),

            # PRs
            ("pr:42", NodeType.PR, "PR #42: Add hello function",
             "PR description",
             '{"number": 42, "state": "merged", "url": "https://github.com/example/repo/pull/42", "ts": "' + timestamp_3 + '"}'),

            ("pr:43", NodeType.PR, "PR #43: Add goodbye function",
             "PR description",
             '{"number": 43, "state": "merged", "url": "https://github.com/example/repo/pull/43", "ts": "' + timestamp_4 + '"}'),

            # Issues
            ("issue:123", NodeType.ISSUE, "Issue #123: Need greeting function",
             "Issue description",
             '{"number": 123, "state": "closed", "url": "https://github.com/example/repo/issues/123", "ts": "' + timestamp_1 + '"}'),

            ("issue:124", NodeType.ISSUE, "Issue #124: Need farewell function",
             "Issue description",
             '{"number": 124, "state": "closed", "url": "https://github.com/example/repo/issues/124", "ts": "' + timestamp_3 + '"}'),

            # ADRs
            ("adr:001", NodeType.ADR, "ADR-001: Greeting Strategy",
             "ADR content",
             '{"status": "Accepted", "decision_makers": ["Test User"], "path": "docs/adr/001-greeting-strategy.md", "ts": "' + timestamp_1 + '"}'),

            ("adr:002", NodeType.ADR, "ADR-002: Farewell Strategy",
             "ADR content",
             '{"status": "Accepted", "decision_makers": ["Test User"], "path": "docs/adr/002-farewell-strategy.md", "ts": "' + timestamp_5 + '"}'),
        ]

        for node_id, node_type, title, body, extra in nodes:
            conn.execute(
                "INSERT INTO nodes (id, type, title, body, extra) VALUES (?, ?, ?, ?, ?)",
                (node_id, node_type, title, body, extra)
            )

        # Insert edges
        edges = [
            # Commit -> File edges
            (f"commit:{commit_hash_1}", "file:test_file.py", EdgeRel.MODIFIES),
            (f"commit:{commit_hash_2}", "file:test_file.py", EdgeRel.MODIFIES),

            # PR -> Commit edges
            ("pr:42", f"commit:{commit_hash_1}", EdgeRel.MERGES),
            ("pr:43", f"commit:{commit_hash_2}", EdgeRel.MERGES),

            # PR -> Issue edges
            ("pr:42", "issue:123", EdgeRel.MENTIONS),
            ("pr:43", "issue:124", EdgeRel.MENTIONS),

            # Issue -> ADR edges
            ("issue:123", "adr:001", EdgeRel.MENTIONS),
            ("issue:124", "adr:002", EdgeRel.MENTIONS),

            # ADR -> File edges
            ("adr:001", "file:test_file.py", EdgeRel.DECIDES),
            ("adr:002", "file:test_file.py", EdgeRel.DECIDES),
        ]

        # APSW connections automatically commit after each statement
        # or when the transaction context manager exits
        with conn:
            for src, dst, rel in edges:
                conn.execute(
                    "INSERT INTO edges (src, dst, rel) VALUES (?, ?, ?)",
                    (src, dst, rel)
                )

    def test_get_commit_for_line_different_lines(self):
        """Test getting commits for different lines."""
        # Change to the repository directory
        original_cwd = os.getcwd()
        os.chdir(self.repo_path)

        try:
            # Line 2 (def hello():) should be from the first commit
            commit_id_1 = get_commit_for_line(self.repo_path, "test_file.py", 2)
            self.assertEqual(commit_id_1, self.commit_hash_1)

            # Line 5 (def goodbye():) should be from the second commit
            commit_id_2 = get_commit_for_line(self.repo_path, "test_file.py", 5)
            self.assertEqual(commit_id_2, self.commit_hash_2)
        finally:
            # Restore the original working directory
            os.chdir(original_cwd)

    def test_trace_history_basic(self):
        """Test basic trace history functionality."""
        # Change to the repository directory
        original_cwd = os.getcwd()
        os.chdir(self.repo_path)

        try:
            # Get a connection to the database
            conn = get_connection(self.db_path)

            # Trace from the first commit
            results = trace_history(conn, "test_file.py", 2, max_nodes=10, max_hops=1)

            # Check that we got some results
            self.assertGreater(len(results), 0)

            # Check that we have a commit in the results
            commit_nodes = [node for node in results if node["type"] == "commit"]
            self.assertGreater(len(commit_nodes), 0)

            # Close the connection
            conn.close()
        finally:
            # Restore the original working directory
            os.chdir(original_cwd)

    def test_trace_history_with_max_hops(self):
        """Test tracing history with different max_hops values."""
        # Change to the repository directory
        original_cwd = os.getcwd()
        os.chdir(self.repo_path)

        try:
            # Get a connection to the database
            conn = get_connection(self.db_path)

            # With max_hops=0, we should only get the commit
            results_0 = trace_history(conn, "test_file.py", 2, max_nodes=10, max_hops=0)
            self.assertGreater(len(results_0), 0)

            # With max_hops=1, we should get more results
            results_1 = trace_history(conn, "test_file.py", 2, max_nodes=10, max_hops=1)
            # We can't guarantee more results, but we should at least get the same number
            self.assertGreaterEqual(len(results_1), len(results_0))

            # Close the connection
            conn.close()
        finally:
            # Restore the original working directory
            os.chdir(original_cwd)

    def test_trace_history_with_max_results(self):
        """Test tracing history with different max_results values."""
        # Change to the repository directory
        original_cwd = os.getcwd()
        os.chdir(self.repo_path)

        try:
            # Get a connection to the database
            conn = get_connection(self.db_path)

            # With max_nodes=1, we should get at most 1 result
            results_1 = trace_history(conn, "test_file.py", 2, max_nodes=1, max_hops=3)
            self.assertLessEqual(len(results_1), 1)

            # With max_nodes=2, we should get at most 2 results
            results_2 = trace_history(conn, "test_file.py", 2, max_nodes=2, max_hops=3)
            self.assertLessEqual(len(results_2), 2)

            # With max_nodes=10, we should get more results
            results_10 = trace_history(conn, "test_file.py", 2, max_nodes=10, max_hops=3)
            # We can't guarantee more results, but we should at least get the same number
            self.assertGreaterEqual(len(results_10), len(results_1))

            # Close the connection
            conn.close()
        finally:
            # Restore the original working directory
            os.chdir(original_cwd)

    def test_trace_history_for_file_line_integration(self):
        """Test the full trace_history_for_file_line function."""
        # Change to the repository directory
        original_cwd = os.getcwd()
        os.chdir(self.repo_path)

        try:
            # Trace history for line 2 (def hello():)
            results = trace_history_for_file_line(
                self.db_path,
                "test_file.py",
                2,
                max_results=10,
                max_hops=3
            )

            # Check that we got some results
            self.assertGreater(len(results), 0)

            # Check that we have a commit in the results
            commit_nodes = [node for node in results if node["type"] == "commit"]
            self.assertGreater(len(commit_nodes), 0)

            # Check that the commit has the expected hash
            commit_node = commit_nodes[0]
            self.assertEqual(commit_node["sha"], self.commit_hash_1)
        finally:
            # Restore the original working directory
            os.chdir(original_cwd)

    def test_trace_history_for_different_file_lines(self):
        """Test tracing history for different lines in the same file."""
        # Change to the repository directory
        original_cwd = os.getcwd()
        os.chdir(self.repo_path)

        try:
            # Trace history for line 2 (def hello():)
            results_1 = trace_history_for_file_line(
                self.db_path,
                "test_file.py",
                2,
                max_results=10,
                max_hops=3
            )

            # Trace history for line 5 (def goodbye():)
            results_2 = trace_history_for_file_line(
                self.db_path,
                "test_file.py",
                5,
                max_results=10,
                max_hops=3
            )

            # Check that we got some results
            self.assertGreater(len(results_1), 0)
            self.assertGreater(len(results_2), 0)

            # Check that we have commit nodes in the results
            commit_nodes_1 = [node for node in results_1 if node["type"] == "commit"]
            commit_nodes_2 = [node for node in results_2 if node["type"] == "commit"]
            self.assertGreater(len(commit_nodes_1), 0)
            self.assertGreater(len(commit_nodes_2), 0)

            # Check that the commits have the expected hashes
            commit_node_1 = commit_nodes_1[0]
            commit_node_2 = commit_nodes_2[0]
            self.assertEqual(commit_node_1["sha"], self.commit_hash_1)
            self.assertEqual(commit_node_2["sha"], self.commit_hash_2)
        finally:
            # Restore the original working directory
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
