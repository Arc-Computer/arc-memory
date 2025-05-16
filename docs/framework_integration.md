# Framework Integration

Arc Memory is designed to work seamlessly with popular agent frameworks through a flexible adapter system. This document explains how to integrate Arc Memory with different frameworks and how to extend it for custom frameworks.

## Framework-Agnostic Design

Arc Memory follows a framework-agnostic design with adapters for popular frameworks:

```
┌─────────────────────────────────────────────────────────┐
│                    Arc Memory SDK                       │
├─────────────┬─────────────┬─────────────┬─────────────┬─┤
│ Core API    │ Query API   │ Temporal    │ Impact      │ │
│             │             │ API         │ API         │ │
└─────────────┴─────────────┴─────────────┴─────────────┴─┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    Adapter Layer                        │
├─────────────┬─────────────┬─────────────┬─────────────┬─┤
│ LangChain   │ OpenAI      │ LlamaIndex  │ Custom      │ │
│ Adapter     │ Adapter     │ Adapter     │ Adapters    │ │
└─────────────┴─────────────┴─────────────┴─────────────┴─┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                  Agent Frameworks                       │
├─────────────┬─────────────┬─────────────┬─────────────┬─┤
│ LangChain   │ OpenAI      │ LlamaIndex  │ Custom      │ │
│             │             │             │ Frameworks  │ │
└─────────────┴─────────────┴─────────────┴─────────────┴─┘
```

This design allows you to:

1. Use Arc Memory directly through its SDK
2. Integrate with your preferred agent framework
3. Create custom adapters for specialized frameworks
4. Switch frameworks without changing your core logic

## Supported Frameworks

### LangChain

Arc Memory integrates with LangChain through a dedicated adapter that converts Arc Memory functions into LangChain tools:

```python
from arc_memory.sdk import Arc
from arc_memory.adapters.langchain import ArcLangChainAdapter

# Initialize Arc Memory
arc = Arc(repo_path="./")

# Create LangChain adapter
adapter = ArcLangChainAdapter(arc)

# Get LangChain tools
tools = adapter.get_tools()

# Create an agent with the tools
agent = create_langchain_agent(llm, tools)

# Run the agent
agent.run("What were the major changes in the last release?")
```

Available LangChain tools include:

- `arc_query`: Ask natural language questions about the codebase
- `arc_get_decision_trail`: Get the decision trail for a specific file and line
- `arc_get_entity_history`: Get the history of an entity
- `arc_analyze_impact`: Analyze the potential impact of changes

### OpenAI

Arc Memory integrates with OpenAI's function calling through a dedicated adapter:

```python
from arc_memory.sdk import Arc
from arc_memory.adapters.openai import ArcOpenAIAdapter
from openai import OpenAI

# Initialize Arc Memory
arc = Arc(repo_path="./")

# Create OpenAI adapter
adapter = ArcOpenAIAdapter(arc)

# Get OpenAI functions
functions = adapter.get_functions()

# Create OpenAI client
client = OpenAI()

# Create a completion with the functions
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What were the major changes in the last release?"}],
    functions=functions,
    function_call="auto"
)
```

Available OpenAI functions include:

- `arc_query`: Ask natural language questions about the codebase
- `arc_get_decision_trail`: Get the decision trail for a specific file and line
- `arc_get_entity_history`: Get the history of an entity
- `arc_analyze_impact`: Analyze the potential impact of changes

### LlamaIndex

Arc Memory integrates with LlamaIndex through a dedicated adapter:

```python
from arc_memory.sdk import Arc
from arc_memory.adapters.llamaindex import ArcLlamaIndexAdapter
from llama_index import VectorStoreIndex, ServiceContext

# Initialize Arc Memory
arc = Arc(repo_path="./")

# Create LlamaIndex adapter
adapter = ArcLlamaIndexAdapter(arc)

# Get LlamaIndex tools
tools = adapter.get_tools()

# Create a query engine with the tools
query_engine = adapter.create_query_engine()

# Query the engine
response = query_engine.query("What were the major changes in the last release?")
```

Available LlamaIndex tools include:

- `arc_query`: Ask natural language questions about the codebase
- `arc_get_decision_trail`: Get the decision trail for a specific file and line
- `arc_get_entity_history`: Get the history of an entity
- `arc_analyze_impact`: Analyze the potential impact of changes

## Creating Custom Adapters

You can create custom adapters for frameworks not officially supported:

```python
from arc_memory.sdk import Arc
from arc_memory.adapters.base import BaseAdapter

class MyCustomAdapter(BaseAdapter):
    """Custom adapter for a specialized framework."""

    def __init__(self, arc: Arc):
        """Initialize the adapter.
        
        Args:
            arc: The Arc Memory instance
        """
        super().__init__(arc)
    
    def get_tools(self):
        """Get tools for the custom framework.
        
        Returns:
            Tools in the format expected by the custom framework
        """
        # Implement conversion from Arc Memory functions to framework tools
        tools = []
        
        # Add query tool
        tools.append({
            "name": "arc_query",
            "description": "Ask natural language questions about the codebase",
            "function": self._wrap_query
        })
        
        # Add more tools as needed
        
        return tools
    
    def _wrap_query(self, query: str):
        """Wrap the query function for the custom framework.
        
        Args:
            query: The query to execute
            
        Returns:
            The query result in the format expected by the custom framework
        """
        result = self.arc.query(query)
        
        # Convert result to the format expected by the custom framework
        return {
            "answer": result.answer,
            "confidence": result.confidence,
            "sources": [source.id for source in result.sources]
        }
```

## Best Practices

### 1. Direct SDK vs. Framework Integration

Choose the right approach for your use case:

- **Direct SDK**: Best for simple scripts, custom workflows, or when you need maximum control
- **Framework Integration**: Best for complex agents, when using existing framework features, or when integrating with a larger system

### 2. Error Handling

Implement robust error handling:

```python
try:
    result = arc.query("What were the major changes in the last release?")
except QueryError as e:
    # Handle query errors
    print(f"Query error: {e}")
except ConnectionError as e:
    # Handle connection errors
    print(f"Connection error: {e}")
except Exception as e:
    # Handle other errors
    print(f"Unexpected error: {e}")
```

### 3. Caching

Use caching to improve performance:

```python
from arc_memory.sdk import Arc
from arc_memory.cache import FileCache

# Initialize Arc Memory with caching
arc = Arc(
    repo_path="./",
    cache=FileCache(cache_dir=".arc_cache")
)
```

### 4. Async Support

Use async methods for better performance in async environments:

```python
import asyncio
from arc_memory.sdk import Arc
from arc_memory.adapters.openai_async import ArcOpenAIAsyncAdapter

async def main():
    # Initialize Arc Memory
    arc = Arc(repo_path="./")
    
    # Create async OpenAI adapter
    adapter = ArcOpenAIAsyncAdapter(arc)
    
    # Get OpenAI functions
    functions = await adapter.get_functions_async()
    
    # Use the functions asynchronously
    # ...

asyncio.run(main())
```

## Framework-Specific Considerations

### LangChain

- Use `ArcLangChainAdapter.get_tools()` to get LangChain tools
- Use `ArcLangChainAdapter.get_retriever()` to get a LangChain retriever
- Use `ArcLangChainAdapter.get_memory()` to get a LangChain memory object

### OpenAI

- Use `ArcOpenAIAdapter.get_functions()` to get OpenAI functions
- Use `ArcOpenAIAdapter.handle_function_call()` to handle function calls
- Use `ArcOpenAIAdapter.create_assistant()` to create an OpenAI assistant

### LlamaIndex

- Use `ArcLlamaIndexAdapter.get_tools()` to get LlamaIndex tools
- Use `ArcLlamaIndexAdapter.get_retriever()` to get a LlamaIndex retriever
- Use `ArcLlamaIndexAdapter.create_query_engine()` to create a query engine

## Conclusion

Arc Memory's framework-agnostic design with adapters makes it easy to integrate with your preferred agent framework. Whether you're using LangChain, OpenAI, LlamaIndex, or a custom framework, Arc Memory provides a consistent experience while leveraging the strengths of each framework.

For more detailed examples, see the [examples directory](../docs/examples/) and the [adapter documentation](../docs/sdk/adapters.md).
