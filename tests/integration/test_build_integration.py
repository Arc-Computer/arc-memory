"""Integration tests for the build process."""

import os
import shutil
import sqlite3
import subprocess
import tempfile
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


class TestBuildIntegration(unittest.TestCase):
    """Integration tests for the build process."""

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
        
        # Create an ADR file
        cls.adr_file = cls.repo_path / "docs" / "adr" / "001-test-decision.md"
        cls.adr_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cls.adr_file, "w") as f:
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
            cwd=cls.repo_path,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add test ADR"],
            cwd=cls.repo_path,
            check=True
        )
        
        # Create a database file
        cls.db_path = cls.repo_path / "graph.db"
    
    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        cls.repo_dir.cleanup()
    
    def test_full_build(self):
        """Test a full build of the knowledge graph."""
        # Build the graph
        node_count, edge_count, plugin_metadata = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,
            days=365,
            incremental=False,
        )
        
        # Check that we have nodes and edges
        self.assertGreater(node_count, 0)
        self.assertGreater(edge_count, 0)
        
        # Check that we have metadata for the git and adr plugins
        self.assertIn("git", plugin_metadata)
        self.assertIn("adr", plugin_metadata)
        
        # Check that the database file exists
        self.assertTrue(self.db_path.exists())
        
        # Check that we can connect to the database
        conn = get_connection(self.db_path)
        
        # Check that we have the expected tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn("nodes", tables)
        self.assertIn("edges", tables)
        
        # Check that we have nodes of the expected types
        cursor.execute("SELECT DISTINCT type FROM nodes")
        node_types = [row[0] for row in cursor.fetchall()]
        self.assertIn(NodeType.COMMIT, node_types)
        self.assertIn(NodeType.FILE, node_types)
        self.assertIn(NodeType.ADR, node_types)
        
        # Check that we have edges of the expected types
        cursor.execute("SELECT DISTINCT rel FROM edges")
        edge_types = [row[0] for row in cursor.fetchall()]
        self.assertIn(EdgeRel.MODIFIES, edge_types)
        
        # Close the connection
        conn.close()
    
    def test_incremental_build(self):
        """Test an incremental build of the knowledge graph."""
        # First, do a full build
        node_count_1, edge_count_1, _ = build_graph(
            repo_path=self.repo_path,
            output_path=self.db_path,
            max_commits=100,
            days=365,
            incremental=False,
        )
        
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
        manifest = load_build_manifest()
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest.node_count, node_count_2)
        self.assertEqual(manifest.edge_count, edge_count_2)
        
        # Check that the database contains the new commit
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes WHERE type = ? AND title LIKE ?", 
                      (NodeType.COMMIT, "%Add goodbye function%"))
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
        conn.close()


if __name__ == "__main__":
    unittest.main()
