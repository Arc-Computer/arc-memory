"""Tests for the Arc class adapter integration.

This module contains tests for the integration of the Arc class with framework adapters.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from arc_memory.sdk.core import Arc
from arc_memory.sdk.errors import FrameworkError, QueryError


class TestArcAdapters(unittest.TestCase):
    """Tests for the Arc class adapter integration."""

    def setUp(self):
        """Set up test environment."""
        # Patch the get_db_adapter function
        self.get_db_adapter_patcher = patch("arc_memory.sdk.core.get_db_adapter")
        self.mock_get_db_adapter = self.get_db_adapter_patcher.start()
        self.mock_adapter = MagicMock()
        self.mock_get_db_adapter.return_value = self.mock_adapter

        # Patch the get_db_path function
        self.get_db_path_patcher = patch("arc_memory.sdk.core.get_db_path")
        self.mock_get_db_path = self.get_db_path_patcher.start()
        self.mock_get_db_path.return_value = "/path/to/db"

        # Create an Arc instance
        self.arc = Arc(repo_path="./")

    def tearDown(self):
        """Clean up test environment."""
        self.get_db_adapter_patcher.stop()
        self.get_db_path_patcher.stop()

    @patch("arc_memory.sdk.core.get_adapter")
    def test_get_adapter(self, mock_get_adapter):
        """Test getting a framework adapter."""
        # Set up the mock
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        # Get the adapter
        adapter = self.arc.get_adapter("langchain")

        # Check that the adapter was returned
        self.assertEqual(adapter, mock_adapter)
        mock_get_adapter.assert_called_once_with("langchain")

    @patch("arc_memory.sdk.core.get_adapter")
    def test_get_adapter_error(self, mock_get_adapter):
        """Test getting a framework adapter with an error."""
        # Set up the mock to raise an exception
        mock_get_adapter.side_effect = Exception("Test error")

        # Try to get the adapter
        with self.assertRaises(FrameworkError) as context:
            self.arc.get_adapter("langchain")

        # Check the error message
        self.assertEqual(str(context.exception), "Failed to get framework adapter: Test error")

    @patch("arc_memory.sdk.core.get_adapter")
    def test_get_tools(self, mock_get_adapter):
        """Test getting tools for a framework."""
        # Set up the mock
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter.adapt_functions.return_value = ["tool1", "tool2"]

        # Get the tools
        tools = self.arc.get_tools("langchain")

        # Check that the tools were returned
        self.assertEqual(tools, ["tool1", "tool2"])
        mock_get_adapter.assert_called_once_with("langchain")
        mock_adapter.adapt_functions.assert_called_once()

        # Check that the correct functions were passed to adapt_functions
        functions = mock_adapter.adapt_functions.call_args[0][0]
        function_names = [func.__name__ for func in functions]

        # Verify expected functions are included
        expected_functions = [
            "query",
            "get_decision_trail",
            "get_related_entities",
            "get_entity_details",
            "analyze_component_impact",
            "get_entity_history"
        ]

        for expected_func in expected_functions:
            self.assertIn(expected_func, function_names,
                          f"Expected function '{expected_func}' not found in adapted functions")

    @patch("arc_memory.sdk.core.get_adapter")
    def test_create_agent(self, mock_get_adapter):
        """Test creating an agent with a framework."""
        # Set up the mock
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter.create_agent.return_value = "agent"

        # Create the agent
        agent = self.arc.create_agent("langchain", param1="value1", param2="value2")

        # Check that the agent was created
        self.assertEqual(agent, "agent")
        mock_get_adapter.assert_called_once_with("langchain")
        mock_adapter.create_agent.assert_called_once_with(param1="value1", param2="value2")

    @patch("arc_memory.sdk.core.get_adapter")
    def test_create_agent_with_tools(self, mock_get_adapter):
        """Test creating an agent with tools."""
        # Set up the mocks
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter.adapt_functions.return_value = ["tool1", "tool2"]
        mock_adapter.create_agent.return_value = "agent_with_tools"

        # Get the tools and create the agent
        tools = self.arc.get_tools("openai")
        agent = self.arc.create_agent("openai", tools=tools)

        # Check that the agent was created with the tools
        self.assertEqual(agent, "agent_with_tools")
        mock_get_adapter.assert_any_call("openai")
        mock_adapter.adapt_functions.assert_called_once()
        mock_adapter.create_agent.assert_called_once_with(tools=["tool1", "tool2"])

    def test_export_graph(self):
        """Test exporting the graph."""
        # Set up the adapter
        self.mock_adapter.db_path = "/path/to/db"

        # Mock the export_graph function
        with patch("arc_memory.export.export_graph") as mock_export_graph:
            # Set up the mock
            mock_export_graph.return_value = Path("/path/to/output.json")

            # Export the graph
            result = self.arc.export_graph(
                pr_sha="abc123",
                output_path="/path/to/output.json",
                compress=True,
                sign=False,
                base_branch="main",
                max_hops=3,
                optimize_for_llm=True,
                include_causal=True
            )

            # Check that the export function was called
            self.assertEqual(result, Path("/path/to/output.json"))
            mock_export_graph.assert_called_once()
            _, kwargs = mock_export_graph.call_args
            self.assertEqual(kwargs["pr_sha"], "abc123")
            self.assertEqual(kwargs["output_path"], Path("/path/to/output.json"))
            self.assertEqual(kwargs["compress"], True)
            self.assertEqual(kwargs["sign"], False)
            self.assertEqual(kwargs["base_branch"], "main")
            self.assertEqual(kwargs["max_hops"], 3)
            self.assertEqual(kwargs["enhance_for_llm"], True)
            self.assertEqual(kwargs["include_causal"], True)

    def test_export_graph_error(self):
        """Test exporting the graph with an error."""
        # Set up the adapter
        self.mock_adapter.db_path = "/path/to/db"

        # Mock the export_graph function
        with patch("arc_memory.export.export_graph") as mock_export_graph:
            # Set up the mock to raise an exception
            mock_export_graph.side_effect = Exception("Test error")

            # Try to export the graph
            with self.assertRaises(QueryError) as context:
                self.arc.export_graph(
                    pr_sha="abc123",
                    output_path="/path/to/output.json"
                )

            # Check the error message
            self.assertEqual(str(context.exception), "Failed to export graph: Test error")


if __name__ == "__main__":
    unittest.main()
