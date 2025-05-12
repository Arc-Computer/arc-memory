"""Framework adapters for Arc Memory SDK.

This package provides adapters for integrating Arc Memory with various agent frameworks.
The adapters adapt Arc Memory functions to framework-specific formats, allowing
seamless integration with various agent frameworks.

Currently supported frameworks:
- LangChain: Supports both legacy AgentExecutor and modern LangGraph agents
- OpenAI: Supports both function calling and the Assistants API

Example with LangChain:
    ```python
    from arc_memory.sdk import Arc
    from langchain_openai import ChatOpenAI

    # Initialize Arc with the repository path
    arc = Arc(repo_path="./")

    # Get Arc Memory functions as LangChain tools
    tools = arc.get_tools("langchain")

    # Create a LangChain agent with Arc Memory tools
    agent = arc.create_agent(
        "langchain",
        llm=ChatOpenAI(model="gpt-4o"),
        system_message="You are a helpful assistant with access to Arc Memory."
    )

    # Use the agent
    response = agent.invoke({"messages": [("human", "What's the decision trail for file.py?")]})
    ```

Example with OpenAI:
    ```python
    from arc_memory.sdk import Arc

    # Initialize Arc with the repository path
    arc = Arc(repo_path="./")

    # Get Arc Memory functions as OpenAI tools
    tools = arc.get_tools("openai")

    # Create an OpenAI agent with Arc Memory tools
    agent = arc.create_agent(
        "openai",
        tools=tools,
        model="gpt-4o",
        system_message="You are a helpful assistant with access to Arc Memory."
    )

    # Use the agent
    response = agent("What's the decision trail for file.py?")

    # Or create an OpenAI Assistant
    assistant = arc.get_adapter("openai").create_assistant(
        tools=tools,
        name="Arc Memory Assistant",
        instructions="You are a helpful assistant with access to Arc Memory."
    )
    ```
"""

from arc_memory.sdk.adapters.base import FrameworkAdapter
from arc_memory.sdk.adapters.registry import (
    get_adapter,
    register_adapter,
    get_all_adapters,
    get_adapter_names,
    discover_adapters,
)

__all__ = [
    "FrameworkAdapter",
    "get_adapter",
    "register_adapter",
    "get_all_adapters",
    "get_adapter_names",
    "discover_adapters",
]
