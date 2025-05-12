"""Framework adapters for Arc Memory SDK.

This package provides adapters for integrating Arc Memory with various agent frameworks.
The adapters convert Arc Memory's return types to framework-specific formats.

Example:
    ```python
    from arc_memory.sdk import Arc
    from arc_memory.sdk.adapters import get_adapter

    # Initialize Arc with the repository path
    arc = Arc(repo_path="./")

    # Get a LangChain adapter
    langchain_adapter = get_adapter("langchain")

    # Use the adapter to convert Arc Memory's return types to LangChain format
    langchain_tool = langchain_adapter.create_tool(arc.query)
    ```
"""

# This will be implemented in a future PR
# from arc_memory.sdk.adapters.registry import get_adapter, register_adapter

# __all__ = ["get_adapter", "register_adapter"]
