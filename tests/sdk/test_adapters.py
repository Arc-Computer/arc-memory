"""Tests for the framework adapters.

This module contains tests for the framework adapter protocol and registry.
"""

import unittest
from typing import List
from unittest.mock import MagicMock, patch

from arc_memory.sdk.adapters.base import FrameworkAdapter
from arc_memory.sdk.adapters.registry import AdapterRegistry
from arc_memory.sdk.errors import AdapterError


class MockAdapter:
    """Mock adapter for testing."""

    def __init__(self, name="mock"):
        """Initialize the mock adapter."""
        self.name = name

    def get_name(self) -> str:
        """Return the name of the adapter."""
        return self.name

    def get_supported_versions(self) -> list:
        """Return a list of supported versions."""
        return ["1.0.0", "1.1.0"]

    def adapt_functions(self, functions):
        """Adapt functions to the framework's format."""
        return [f.__name__ for f in functions]

    def create_agent(self, **kwargs):
        """Create an agent using the framework."""
        return {"name": self.name, "kwargs": kwargs}


class TestAdapterRegistry(unittest.TestCase):
    """Tests for the AdapterRegistry class."""

    def test_register_and_get(self):
        """Test registering and getting adapters."""
        registry = AdapterRegistry()
        adapter = MockAdapter()

        # Register the adapter
        registry.register(adapter)

        # Get the adapter
        retrieved = registry.get("mock")
        self.assertEqual(retrieved, adapter)

    def test_register_duplicate(self):
        """Test registering a duplicate adapter."""
        registry = AdapterRegistry()
        adapter1 = MockAdapter()
        adapter2 = MockAdapter()

        # Register the first adapter
        registry.register(adapter1)

        # Try to register a duplicate adapter
        with self.assertRaises(AdapterError):
            registry.register(adapter2)

    def test_get_nonexistent(self):
        """Test getting a nonexistent adapter."""
        registry = AdapterRegistry()

        # Try to get a nonexistent adapter
        retrieved = registry.get("nonexistent")
        self.assertIsNone(retrieved)

    def test_get_all(self):
        """Test getting all adapters."""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("mock1")
        adapter2 = MockAdapter("mock2")

        # Register the adapters
        registry.register(adapter1)
        registry.register(adapter2)

        # Get all adapters
        adapters = registry.get_all()
        self.assertEqual(len(adapters), 2)
        self.assertIn(adapter1, adapters)
        self.assertIn(adapter2, adapters)

    def test_get_names(self):
        """Test getting adapter names."""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("mock1")
        adapter2 = MockAdapter("mock2")

        # Register the adapters
        registry.register(adapter1)
        registry.register(adapter2)

        # Get adapter names
        names = registry.get_names()
        self.assertEqual(len(names), 2)
        self.assertIn("mock1", names)
        self.assertIn("mock2", names)

    @patch("importlib.metadata.entry_points")
    def test_discover(self, mock_entry_points):
        """Test discovering adapters from entry points."""
        # Create a mock entry point
        mock_entry_point = MagicMock()
        mock_entry_point.name = "mock"
        mock_entry_point.load.return_value = MockAdapter

        # Set up the mock to return our mock entry point for Python 3.10+ syntax
        mock_entry_points.return_value = [mock_entry_point]

        # Discover adapters
        registry = AdapterRegistry.discover()

        # Check that the adapter was discovered
        self.assertEqual(len(registry.get_names()), 1)
        self.assertIn("mock", registry.get_names())
        adapter = registry.get("mock")
        self.assertEqual(adapter.get_name(), "mock")
        self.assertEqual(adapter.get_supported_versions(), ["1.0.0", "1.1.0"])


class TestLangChainAdapter(unittest.TestCase):
    """Tests for the LangChainAdapter class."""

    def test_get_name(self):
        """Test getting the adapter name."""
        from arc_memory.sdk.adapters.langchain import LangChainAdapter
        adapter = LangChainAdapter()
        self.assertEqual(adapter.get_name(), "langchain")

    def test_get_supported_versions(self):
        """Test getting supported versions."""
        from arc_memory.sdk.adapters.langchain import LangChainAdapter
        adapter = LangChainAdapter()
        versions = adapter.get_supported_versions()
        self.assertIsInstance(versions, list)
        self.assertTrue(all(isinstance(v, str) for v in versions))

    def test_adapt_functions(self):
        """Test adapting functions to LangChain tools."""
        # Import the adapter
        from arc_memory.sdk.adapters.langchain import LangChainAdapter
        adapter = LangChainAdapter()

        # Create a mock Tool class
        mock_tool = MagicMock()
        mock_tool.return_value = MagicMock()

        # Patch the try/except block in adapt_functions
        original_adapt_functions = adapter.adapt_functions

        def mock_adapt_functions(functions):
            tools = []
            for func in functions:
                tool = mock_tool(
                    name=func.__name__,
                    func=func,
                    description=func.__doc__
                )
                tools.append(tool)
            return tools

        adapter.adapt_functions = mock_adapt_functions

        # Create mock functions
        def func1(): pass
        def func2(): pass

        # Adapt the functions
        tools = adapter.adapt_functions([func1, func2])

        # Check that the tools were created
        self.assertEqual(len(tools), 2)
        mock_tool.assert_any_call(name="func1", func=func1, description=func1.__doc__)
        mock_tool.assert_any_call(name="func2", func=func2, description=func2.__doc__)

        # Restore original method
        adapter.adapt_functions = original_adapt_functions

    def test_create_agent_langgraph(self):
        """Test creating a LangChain agent with LangGraph."""
        # Import the adapter
        from arc_memory.sdk.adapters.langchain import LangChainAdapter

        # Create mocks
        mock_langgraph = MagicMock(return_value="langgraph_agent")
        mock_legacy = MagicMock()

        # Create adapter and replace methods with mocks
        adapter = LangChainAdapter()
        adapter._create_langgraph_agent = mock_langgraph
        adapter._create_legacy_agent = mock_legacy

        # Create the agent
        agent = adapter.create_agent(tools=["tool1", "tool2"])

        # Check that the LangGraph agent was created
        self.assertEqual(agent, "langgraph_agent")
        mock_langgraph.assert_called_once()
        self.assertEqual(mock_langgraph.call_args[1]["tools"], ["tool1", "tool2"])
        mock_legacy.assert_not_called()

    def test_create_agent_legacy(self):
        """Test creating a LangChain agent with legacy AgentExecutor."""
        # Import the adapter
        from arc_memory.sdk.adapters.langchain import LangChainAdapter

        # Create mocks
        mock_langgraph = MagicMock(side_effect=ImportError("LangGraph not installed"))
        mock_legacy = MagicMock(return_value="legacy_agent")

        # Create adapter and replace methods with mocks
        adapter = LangChainAdapter()
        adapter._create_langgraph_agent = mock_langgraph
        adapter._create_legacy_agent = mock_legacy

        # Create the agent
        agent = adapter.create_agent(tools=["tool1", "tool2"])

        # Check that the legacy agent was created
        self.assertEqual(agent, "legacy_agent")
        mock_langgraph.assert_called_once()
        self.assertEqual(mock_langgraph.call_args[1]["tools"], ["tool1", "tool2"])
        mock_legacy.assert_called_once()
        self.assertEqual(mock_legacy.call_args[1]["tools"], ["tool1", "tool2"])


class TestOpenAIAdapter(unittest.TestCase):
    """Tests for the OpenAIAdapter class."""

    def test_get_name(self):
        """Test getting the adapter name."""
        from arc_memory.sdk.adapters.openai import OpenAIAdapter
        adapter = OpenAIAdapter()
        self.assertEqual(adapter.get_name(), "openai")

    def test_get_supported_versions(self):
        """Test getting supported versions."""
        from arc_memory.sdk.adapters.openai import OpenAIAdapter
        adapter = OpenAIAdapter()
        versions = adapter.get_supported_versions()
        self.assertIsInstance(versions, list)
        self.assertTrue(all(isinstance(v, str) for v in versions))

    def test_adapt_functions(self):
        """Test adapting functions to OpenAI tool definitions."""
        # Import the adapter
        from arc_memory.sdk.adapters.openai import OpenAIAdapter
        adapter = OpenAIAdapter()

        # Create mock functions
        def func1(param1: str, param2: int = 0): pass
        def func2(param1: bool, param2: List[str] = None): pass

        # Adapt the functions
        tools = adapter.adapt_functions([func1, func2])

        # Check that the tool definitions were created
        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0]["type"], "function")
        self.assertEqual(tools[0]["function"]["name"], "func1")
        self.assertEqual(tools[0]["function"]["parameters"]["type"], "object")
        self.assertEqual(tools[0]["function"]["parameters"]["properties"]["param1"]["type"], "string")
        self.assertEqual(tools[0]["function"]["parameters"]["properties"]["param2"]["type"], "integer")
        self.assertEqual(tools[0]["function"]["parameters"]["required"], ["param1"])

        self.assertEqual(tools[1]["type"], "function")
        self.assertEqual(tools[1]["function"]["name"], "func2")
        self.assertEqual(tools[1]["function"]["parameters"]["type"], "object")
        self.assertEqual(tools[1]["function"]["parameters"]["properties"]["param1"]["type"], "boolean")
        self.assertEqual(tools[1]["function"]["parameters"]["properties"]["param2"]["type"], "array")
        self.assertEqual(tools[1]["function"]["parameters"]["required"], ["param1"])

    def test_create_agent(self):
        """Test creating an OpenAI agent."""
        # Import the adapter
        from arc_memory.sdk.adapters.openai import OpenAIAdapter
        adapter = OpenAIAdapter()

        # Create a mock client
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = "response"

        # Create a mock OpenAI class
        mock_openai = MagicMock(return_value=mock_client)

        # Patch the import in the create_agent method
        original_create_agent = adapter.create_agent

        def mock_create_agent(**kwargs):
            # Create a callable that simulates the agent
            def agent(query):
                # Simulate calling the OpenAI API
                mock_client.chat.completions.create(
                    model=kwargs.get("model", "gpt-4o"),
                    messages=[{"role": "user", "content": query}],
                    tools=kwargs.get("tools", []),
                    tool_choice="auto"
                )
                return "response"
            return agent

        adapter.create_agent = mock_create_agent

        # Create the agent
        agent = adapter.create_agent(tools=["tool1", "tool2"])

        # Call the agent
        agent("test query")

        # Check that the OpenAI API was called correctly
        mock_client.chat.completions.create.assert_called_once()
        _, kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(kwargs["model"], "gpt-4o")
        self.assertEqual(kwargs["tools"], ["tool1", "tool2"])
        self.assertEqual(kwargs["tool_choice"], "auto")

        # Restore original method
        adapter.create_agent = original_create_agent

    def test_create_assistant(self):
        """Test creating an OpenAI Assistant."""
        # Import the adapter
        from arc_memory.sdk.adapters.openai import OpenAIAdapter
        adapter = OpenAIAdapter()

        # Create a mock client
        mock_client = MagicMock()
        mock_client.beta.assistants.create.return_value = "assistant"

        # Create a mock OpenAI class
        mock_openai = MagicMock(return_value=mock_client)

        # Patch the import in the create_assistant method
        original_create_assistant = adapter.create_assistant

        def mock_create_assistant(**kwargs):
            # Simulate creating an assistant
            mock_client.beta.assistants.create(
                name=kwargs.get("name", "Arc Memory Assistant"),
                instructions=kwargs.get("instructions", "You are a helpful assistant with access to Arc Memory."),
                model=kwargs.get("model", "gpt-4o"),
                tools=kwargs.get("tools", [])
            )
            return "assistant"

        adapter.create_assistant = mock_create_assistant

        # Create the assistant
        adapter.create_assistant(tools=["tool1", "tool2"])

        # Check that the OpenAI API was called correctly
        mock_client.beta.assistants.create.assert_called_once()
        _, kwargs = mock_client.beta.assistants.create.call_args
        self.assertEqual(kwargs["name"], "Arc Memory Assistant")
        self.assertEqual(kwargs["model"], "gpt-4o")
        self.assertEqual(kwargs["tools"], ["tool1", "tool2"])

        # Restore original method
        adapter.create_assistant = original_create_assistant


if __name__ == "__main__":
    unittest.main()
