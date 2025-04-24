"""Integration tests for incremental builds."""

import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from arc_memory.plugins import discover_plugins
from arc_memory.schema.models import NodeType, EdgeRel
from arc_memory.sql.db import (
    get_connection,
    get_node_count,
    get_edge_count,
    load_build_manifest,
)
from tests.benchmark.build_helper import build_graph


class TestIncrementalBuild(unittest.TestCase):
    """Integration tests for incremental builds."""

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
        
        # Create a database file
        cls.db_path = cls.repo_path / "graph.db"
    
    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        cls.repo_dir.cleanup()
    
    def test_incremental_build_with_new_commit(self):
        """Test incremental build with a new commit."""
        # First, do a full build
        node_count_1, edge_count_1, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,
            days=365,
            incremental=False,
        )
        
        # Record the build time
        build_manifest_1 = load_build_manifest()
        build_time_1 = build_manifest_1.build_time
        
        # Wait a moment to ensure timestamps are different
        time.sleep(1)
        
        # Now, modify a file and commit it
        with open(self.test_file, "a") as f:
            f.write("\ndef goodbye():\n")
            f.write("    return 'Goodbye, World!'\n")
        
        subprocess.run(
            ["git", "add", "test_file.py"],
            cwd=self.repo_path,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add goodbye function"],
            cwd=self.repo_path,
            check=True
        )
        
        # Do an incremental build
        node_count_2, edge_count_2, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,
            days=365,
            incremental=True,
        )
        
        # Check that we have more nodes and edges
        self.assertGreater(node_count_2, node_count_1)
        self.assertGreater(edge_count_2, edge_count_1)
        
        # Check that the build manifest was updated
        build_manifest_2 = load_build_manifest()
        self.assertIsNotNone(build_manifest_2)
        self.assertEqual(build_manifest_2.node_count, node_count_2)
        self.assertEqual(build_manifest_2.edge_count, edge_count_2)
        self.assertGreater(build_manifest_2.build_time, build_time_1)
        
        # Check that the database contains the new commit
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes WHERE type = ? AND title LIKE ?", 
                      (NodeType.COMMIT, "%Add goodbye function%"))
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
        conn.close()
    
    def test_incremental_build_with_new_adr(self):
        """Test incremental build with a new ADR."""
        # First, do a full build
        node_count_1, edge_count_1, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,
            days=365,
            incremental=False,
        )
        
        # Create an ADR file
        adr_dir = self.repo_path / "docs" / "adr"
        adr_dir.mkdir(parents=True, exist_ok=True)
        adr_file = adr_dir / "001-test-decision.md"
        with open(adr_file, "w") as f:
            f.write("---\n")
            f.write("status: Accepted\n")
            f.write("date: 2023-04-23\n")
            f.write("decision_makers: Test User\n")
            f.write("---\n\n")
            f.write("# ADR-001: Test Decision\n\n")
            f.write("## Context\n\n")
            f.write("This is a test ADR.\n\n")
            f.write("## Decision\n\n")
            f.write("We decided to test the ADR plugin.\n\n")
            f.write("## Consequences\n\n")
            f.write("The ADR plugin will be tested.\n")
        
        # Commit the ADR file
        subprocess.run(
            ["git", "add", "docs/adr/001-test-decision.md"],
            cwd=self.repo_path,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add test ADR"],
            cwd=self.repo_path,
            check=True
        )
        
        # Do an incremental build
        node_count_2, edge_count_2, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,
            days=365,
            incremental=True,
        )
        
        # Check that we have more nodes and edges
        self.assertGreater(node_count_2, node_count_1)
        self.assertGreater(edge_count_2, edge_count_1)
        
        # Check that the database contains the new ADR
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes WHERE type = ?", (NodeType.ADR,))
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0)
        conn.close()
    
    def test_incremental_build_with_no_changes(self):
        """Test incremental build with no changes."""
        # First, do a full build
        node_count_1, edge_count_1, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,
            days=365,
            incremental=False,
        )
        
        # Record the build time
        build_manifest_1 = load_build_manifest()
        build_time_1 = build_manifest_1.build_time
        
        # Wait a moment to ensure timestamps are different
        time.sleep(1)
        
        # Do an incremental build with no changes
        node_count_2, edge_count_2, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,
            days=365,
            incremental=True,
        )
        
        # Check that the node and edge counts are the same
        self.assertEqual(node_count_2, node_count_1)
        self.assertEqual(edge_count_2, edge_count_1)
        
        # Check that the build manifest was updated with a new timestamp
        build_manifest_2 = load_build_manifest()
        self.assertIsNotNone(build_manifest_2)
        self.assertEqual(build_manifest_2.node_count, node_count_2)
        self.assertEqual(build_manifest_2.edge_count, edge_count_2)
        self.assertGreater(build_manifest_2.build_time, build_time_1)
    
    def test_incremental_build_after_full_build_with_limits(self):
        """Test incremental build after a full build with limits."""
        # First, do a full build with limited commits
        node_count_1, edge_count_1, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=1,  # Only process the most recent commit
            days=365,
            incremental=False,
        )
        
        # Now, do an incremental build with more commits
        node_count_2, edge_count_2, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,  # Process more commits
            days=365,
            incremental=True,
        )
        
        # The counts should be the same since incremental builds only process new data
        self.assertEqual(node_count_2, node_count_1)
        self.assertEqual(edge_count_2, edge_count_1)
        
        # Now, do a full build with more commits
        node_count_3, edge_count_3, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,  # Process more commits
            days=365,
            incremental=False,  # Full build
        )
        
        # The counts should be greater since we're processing more commits
        self.assertGreaterEqual(node_count_3, node_count_2)
        self.assertGreaterEqual(edge_count_3, edge_count_2)


if __name__ == "__main__":
    unittest.main()
