# Framework Adapters

Connect Arc Memory to agent frameworks like LangChain and OpenAI using our built-in adapters. This guide covers using existing adapters and creating custom ones for other frameworks.

## Built-in Adapters

Arc Memory comes with built-in adapters for popular agent frameworks:

- **LangChain**: Supports both legacy AgentExecutor and modern LangGraph agents
- **OpenAI**: Supports both function calling and the Assistants API

### Using the LangChain Adapter

```python
from arc_memory import Arc
from langchain_openai import ChatOpenAI

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Get Arc Memory functions as LangChain tools
from arc_memory.sdk.adapters import get_adapter
langchain_adapter = get_adapter("langchain")
tools = langchain_adapter.adapt_functions([
    arc.query,
    arc.get_decision_trail,
    arc.get_related_entities,
    arc.get_entity_details,
    arc.analyze_component_impact
])

# Create a LangChain agent with Arc Memory tools
llm = ChatOpenAI(model="gpt-4o")
agent = langchain_adapter.create_agent(
    tools=tools,
    llm=llm,
    system_message="You are a helpful assistant with access to Arc Memory.",
    verbose=True
)

# Use the agent
response = agent.invoke({"input": "What's the decision trail for src/auth/login.py line 42?"})
print(response)
```

The LangChain adapter supports both the newer LangGraph approach and the legacy AgentExecutor approach:

```python
# Using LangGraph (newer approach)
from langchain_core.messages import HumanMessage
response = agent.invoke([
    HumanMessage(content="What's the decision trail for src/auth/login.py line 42?")
])
print(response)

# Using legacy AgentExecutor
agent = langchain_adapter.create_agent(
    tools=tools,
    llm=llm,
    agent_type="zero-shot-react-description",
    verbose=True
)
response = agent.run("What's the decision trail for src/auth/login.py line 42?")
print(response)
```

### Using the OpenAI Adapter

```python
from arc_memory import Arc

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Get Arc Memory functions as OpenAI tools
from arc_memory.sdk.adapters import get_adapter
openai_adapter = get_adapter("openai")
tools = openai_adapter.adapt_functions([
    arc.query,
    arc.get_decision_trail,
    arc.get_related_entities,
    arc.get_entity_details,
    arc.analyze_component_impact
])

# Create an OpenAI agent with Arc Memory tools
agent = openai_adapter.create_agent(
    tools=tools,
    model="gpt-4o",
    temperature=0,
    system_message="You are a helpful assistant with access to Arc Memory."
)

# Use the agent
response = agent("What's the decision trail for src/auth/login.py line 42?")
print(response)
```

The OpenAI adapter also supports the Assistants API:

```python
# Create an OpenAI Assistant
assistant = openai_adapter.create_assistant(
    tools=tools,
    name="Arc Memory Assistant",
    instructions="You are a helpful assistant with access to Arc Memory.",
    model="gpt-4o"
)
print(f"Assistant created: {assistant.id}")
```

## Adapter Registry

Arc Memory uses a registry to manage framework adapters. You can use the registry to:

- Get an adapter by name
- Register a custom adapter
- Discover all available adapters

```python
from arc_memory.sdk.adapters import (
    get_adapter,
    register_adapter,
    get_all_adapters,
    get_adapter_names,
    discover_adapters
)

# Get an adapter by name
langchain_adapter = get_adapter("langchain")

# Get all registered adapters
adapters = get_all_adapters()

# Get the names of all registered adapters
adapter_names = get_adapter_names()

# Discover and register all available adapters
discovered_adapters = discover_adapters()
```

## Creating a Custom Adapter

You can create a custom adapter for a framework that isn't supported out of the box. To do this, you need to implement the `FrameworkAdapter` protocol:

```python
from typing import Any, Callable, Dict, List
from arc_memory.sdk.adapters.base import FrameworkAdapter
from arc_memory.sdk.adapters import register_adapter

class CustomAdapter(FrameworkAdapter):
    """Adapter for integrating Arc Memory with a custom framework."""

    def get_name(self) -> str:
        """Return a unique name for this adapter."""
        return "custom"

    def get_version(self) -> str:
        """Return the version of this adapter."""
        return "0.1.0"

    def get_framework_name(self) -> str:
        """Return the name of the framework this adapter supports."""
        return "CustomFramework"

    def get_framework_version(self) -> str:
        """Return the version of the framework this adapter supports."""
        return "1.0.0"

    def convert_query_result(self, result: Any) -> Any:
        """Convert a QueryResult to a framework-specific format."""
        # Implement conversion logic
        return result

    def convert_entity_details(self, details: Any) -> Any:
        """Convert EntityDetails to a framework-specific format."""
        # Implement conversion logic
        return details

    def convert_graph_statistics(self, stats: Any) -> Any:
        """Convert GraphStatistics to a framework-specific format."""
        # Implement conversion logic
        return stats

    def create_tool(self, func: Callable, **kwargs) -> Any:
        """Create a framework-specific tool from an Arc Memory function."""
        # Implement tool creation logic
        return {
            "name": func.__name__,
            "description": func.__doc__,
            "function": func
        }

    def adapt_functions(self, functions: List[Callable]) -> List[Any]:
        """Adapt Arc Memory functions to framework-specific tools."""
        return [self.create_tool(func) for func in functions]

    def create_agent(self, **kwargs) -> Any:
        """Create an agent using the framework."""
        # Implement agent creation logic
        tools = kwargs.get("tools", [])
        # Create and return an agent
        return lambda query: f"Agent response to: {query}"

# Register the custom adapter
register_adapter(CustomAdapter())
```

## Using Adapters with Entry Points

You can also make your custom adapter discoverable by other packages by registering it as an entry point in your package's `pyproject.toml`:

```toml
[project.entry-points."arc_memory.plugins.frameworks"]
custom = "my_package.adapters:CustomAdapter"
```

This allows Arc Memory to discover and register your adapter automatically when it's installed.

## Adapter Protocol

The `FrameworkAdapter` protocol defines the interface that all framework adapters must implement:

```python
class FrameworkAdapter(Protocol):
    """Protocol defining the interface for framework adapters."""

    def get_name(self) -> str:
        """Return a unique name for this adapter."""
        ...

    def get_version(self) -> str:
        """Return the version of this adapter."""
        ...

    def get_framework_name(self) -> str:
        """Return the name of the framework this adapter supports."""
        ...

    def get_framework_version(self) -> str:
        """Return the version of the framework this adapter supports."""
        ...

    def convert_query_result(self, result: Any) -> Any:
        """Convert a QueryResult to a framework-specific format."""
        ...

    def convert_entity_details(self, details: Any) -> Any:
        """Convert EntityDetails to a framework-specific format."""
        ...

    def convert_graph_statistics(self, stats: Any) -> Any:
        """Convert GraphStatistics to a framework-specific format."""
        ...

    def create_tool(self, func: Callable, **kwargs) -> Any:
        """Create a framework-specific tool from an Arc Memory function."""
        ...

    def adapt_functions(self, functions: List[Callable]) -> List[Any]:
        """Adapt Arc Memory functions to framework-specific tools."""
        ...
```

Not all methods need to be implemented for a functional adapter. The most important methods are:

- `get_name()`: Returns a unique name for the adapter
- `adapt_functions()`: Adapts Arc Memory functions to framework-specific tools
- `create_agent()`: Creates an agent using the framework
