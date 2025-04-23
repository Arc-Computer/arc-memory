"""Tests for the plugin architecture."""

import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from arc_memory.plugins import IngestorRegistry, discover_plugins
from arc_memory.schema.models import Edge, Node, NodeType, EdgeRel


class MockPlugin:
    """Mock plugin for testing."""
    
    def __init__(self, name: str, node_types: List[str], edge_types: List[str]):
        """Initialize the mock plugin."""
        self.name = name
        self.node_types = node_types
        self.edge_types = edge_types
        self.ingest_called = False
        self.ingest_args = None
    
    def get_name(self) -> str:
        """Return the name of this plugin."""
        return self.name
    
    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return self.node_types
    
    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return self.edge_types
    
    def ingest(
        self,
        repo_path: Path,
        last_processed: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Mock ingest method."""
        self.ingest_called = True
        self.ingest_args = {
            "repo_path": repo_path,
            "last_processed": last_processed,
            **kwargs
        }
        return [], [], {"plugin": self.name}


class TestPluginArchitecture(unittest.TestCase):
    """Test the plugin architecture."""
    
    def test_registry(self):
        """Test the plugin registry."""
        # Create a registry
        registry = IngestorRegistry()
        self.assertEqual(registry.list_plugins(), [])
        
        # Register plugins
        plugin1 = MockPlugin("plugin1", [NodeType.COMMIT], [EdgeRel.MODIFIES])
        plugin2 = MockPlugin("plugin2", [NodeType.PR], [EdgeRel.MENTIONS])
        
        registry.register(plugin1)
        registry.register(plugin2)
        
        # Check list_plugins
        self.assertEqual(registry.list_plugins(), ["plugin1", "plugin2"])
        
        # Check get
        self.assertEqual(registry.get("plugin1"), plugin1)
        self.assertEqual(registry.get("plugin2"), plugin2)
        self.assertIsNone(registry.get("nonexistent"))
        
        # Check get_all
        all_plugins = registry.get_all()
        self.assertEqual(len(all_plugins), 2)
        self.assertIn(plugin1, all_plugins)
        self.assertIn(plugin2, all_plugins)
        
        # Check get_by_node_type
        commit_plugins = registry.get_by_node_type(NodeType.COMMIT)
        self.assertEqual(len(commit_plugins), 1)
        self.assertEqual(commit_plugins[0], plugin1)
        
        pr_plugins = registry.get_by_node_type(NodeType.PR)
        self.assertEqual(len(pr_plugins), 1)
        self.assertEqual(pr_plugins[0], plugin2)
        
        # Check get_by_edge_type
        modifies_plugins = registry.get_by_edge_type(EdgeRel.MODIFIES)
        self.assertEqual(len(modifies_plugins), 1)
        self.assertEqual(modifies_plugins[0], plugin1)
        
        mentions_plugins = registry.get_by_edge_type(EdgeRel.MENTIONS)
        self.assertEqual(len(mentions_plugins), 1)
        self.assertEqual(mentions_plugins[0], plugin2)
    
    def test_discover_plugins(self):
        """Test the discover_plugins function."""
        # This test will discover the built-in plugins
        registry = discover_plugins()
        
        # Check that we have at least the built-in plugins
        plugins = registry.list_plugins()
        self.assertIn("git", plugins)
        self.assertIn("github", plugins)
        self.assertIn("adr", plugins)
        
        # Check that the plugins have the expected node types
        git_plugin = registry.get("git")
        self.assertIsNotNone(git_plugin)
        self.assertIn(NodeType.COMMIT, git_plugin.get_node_types())
        
        github_plugin = registry.get("github")
        self.assertIsNotNone(github_plugin)
        self.assertIn(NodeType.PR, github_plugin.get_node_types())
        
        adr_plugin = registry.get("adr")
        self.assertIsNotNone(adr_plugin)
        self.assertIn(NodeType.ADR, adr_plugin.get_node_types())


if __name__ == "__main__":
    unittest.main()
