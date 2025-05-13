# Arc Memory SDK Examples

This document provides comprehensive examples of using the Arc Memory SDK for various use cases.

## Basic SDK Usage

### Initializing Arc

```python
from arc_memory import Arc

# Initialize with a repository path
arc = Arc(repo_path="./")

# Initialize with a specific database adapter
arc = Arc(repo_path="./", adapter_type="sqlite")

# Initialize with custom connection parameters
arc = Arc(
    repo_path="./",
    adapter_type="neo4j",
    connection_params={
        "uri": "neo4j://localhost:7687",
        "auth": ("neo4j", "password"),
        "database": "arc_memory"
    }
)

# Use as a context manager
with Arc(repo_path="./") as arc:
    result = arc.query("Why was the authentication system refactored?")
```

### Querying the Knowledge Graph

```python
# Simple query
result = arc.query("Why was the authentication system refactored?")
print(result.answer)

# Advanced query with options
result = arc.query(
    question="What were the key decisions behind the API redesign?",
    max_results=10,
    max_hops=5,
    include_causal=True,
    cache=True
)

print(f"Answer: {result.answer}")
print(f"Confidence: {result.confidence}")
print(f"Query Understanding: {result.query_understanding}")
print(f"Reasoning: {result.reasoning}")
print(f"Execution Time: {result.execution_time} seconds")
print("Evidence:")
for evidence in result.evidence:
    print(f"- {evidence['title']}")
```

### Tracing Decision Trails

```python
# Get the decision trail for a specific line in a file
decision_trail = arc.get_decision_trail(
    file_path="src/auth/login.py",
    line_number=42
)

for entry in decision_trail:
    print(f"{entry.title}: {entry.rationale}")

# Advanced decision trail analysis
decision_trail = arc.get_decision_trail(
    file_path="src/auth/login.py",
    line_number=42,
    max_results=10,
    max_hops=5,
    include_rationale=True,
    cache=True
)

for entry in decision_trail:
    print(f"{entry.title}: {entry.rationale}")
    print(f"Importance: {entry.importance}")
    print(f"Position: {entry.trail_position}")
    print(f"Timestamp: {entry.timestamp}")
    print("Related Entities:")
    for related in entry.related_entities:
        print(f"- {related.title} ({related.relationship})")
    print("---")
```

### Exploring Entity Relationships

```python
# Get entities related to a specific entity
related = arc.get_related_entities(entity_id="commit:abc123")
for entity in related:
    print(f"{entity.title} ({entity.relationship})")

# Filter by relationship type and direction
related = arc.get_related_entities(
    entity_id="commit:abc123",
    relationship_types=["DEPENDS_ON", "IMPLEMENTS"],
    direction="outgoing",
    max_results=10,
    include_properties=True
)

for entity in related:
    print(f"{entity.title} ({entity.relationship})")
    print(f"Direction: {entity.direction}")
    print(f"Properties: {entity.properties}")
    print("---")

# Get detailed information about an entity
entity = arc.get_entity_details(
    entity_id="commit:abc123",
    include_related=True
)

print(f"ID: {entity.id}")
print(f"Type: {entity.type}")
print(f"Title: {entity.title}")
print(f"Body: {entity.body}")
print(f"Timestamp: {entity.timestamp}")
print("Properties:")
for key, value in entity.properties.items():
    print(f"- {key}: {value}")
print("Related Entities:")
for related in entity.related_entities:
    print(f"- {related.title} ({related.relationship})")
```

### Analyzing Component Impact

```python
# Analyze the potential impact of changes to a component
impact = arc.analyze_component_impact(component_id="file:src/auth/login.py")
for component in impact:
    print(f"{component.title}: {component.impact_score}")

# Advanced impact analysis
impact = arc.analyze_component_impact(
    component_id="file:src/auth/login.py",
    impact_types=["direct", "indirect", "potential"],
    max_depth=5,
    cache=True
)

for component in impact:
    print(f"{component.title}: {component.impact_score}")
    print(f"Impact Type: {component.impact_type}")
    print(f"Impact Path: {' -> '.join(component.impact_path)}")
    print("Properties:")
    for key, value in component.properties.items():
        print(f"- {key}: {value}")
    print("---")
```

### Temporal Analysis

```python
# Get the history of an entity over time
history = arc.get_entity_history(entity_id="file:src/auth/login.py")
for entry in history:
    print(f"{entry.timestamp}: {entry.title}")

# Advanced temporal analysis
history = arc.get_entity_history(
    entity_id="file:src/auth/login.py",
    start_date="2023-01-01",
    end_date="2023-12-31",
    include_related=True,
    cache=True
)

for entry in history:
    print(f"{entry.timestamp}: {entry.title}")
    print(f"Change Type: {entry.change_type}")
    print(f"Previous Version: {entry.previous_version}")
    print("Related Entities:")
    for related in entry.related_entities:
        print(f"- {related.title} ({related.relationship})")
    print("---")
```

### Exporting the Knowledge Graph

```python
# Export for a specific PR (optimized for GitHub App)
export_path = arc.export_graph(
    pr_sha="abc123",  # PR head commit SHA
    output_path="pr_knowledge_graph.json",
    compress=True,
    sign=True,
    key_id="your-gpg-key-id",
    base_branch="main",
    max_hops=3,
    enhance_for_llm=True,
    include_causal=True
)
print(f"Exported PR knowledge graph to: {export_path}")

# Export with minimal options
export_path = arc.export_graph(
    pr_sha="abc123",
    output_path="simple_export.json"
)
print(f"Exported knowledge graph to: {export_path}")

# If using the SDK export module directly
from arc_memory.sdk.export import export_knowledge_graph
from datetime import datetime

export_result = export_knowledge_graph(
    adapter=arc.adapter,
    repo_path=arc.repo_path,
    output_path="detailed_export.json",
    pr_sha="abc123",
    entity_types=["COMMIT", "PR", "ISSUE"],
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    format="json",
    compress=True,
    sign=True,
    key_id="your-gpg-key-id",
    base_branch="main",
    max_hops=5,
    optimize_for_llm=True,
    include_causal=True
)

print(f"Exported {export_result.entity_count} entities and {export_result.relationship_count} relationships")
print(f"Output path: {export_result.output_path}")
print(f"Format: {export_result.format}")
print(f"Compressed: {export_result.compressed}")
print(f"Signed: {export_result.signed}")
print(f"Signature path: {export_result.signature_path}")
print(f"Execution time: {export_result.execution_time} seconds")
```

## Framework Integration Examples

### LangChain Integration

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

# Create a LangChain agent with Arc Memory tools (auto-detect best approach)
llm = ChatOpenAI(model="gpt-4o")
agent = langchain_adapter.create_agent(
    tools=tools,
    llm=llm,
    system_message="You are a helpful assistant with access to Arc Memory.",
    verbose=True
)

# Use the agent with a simple query
response = agent.invoke({"input": "What's the decision trail for src/auth/login.py line 42?"})
print(response)

# Using structured messages (recommended approach)
from langchain_core.messages import HumanMessage, SystemMessage

messages = [
    SystemMessage(content="You are a helpful assistant with access to Arc Memory."),
    HumanMessage(content="What's the decision trail for src/auth/login.py line 42?")
]
response = agent.invoke(messages)
print(response)

# Explicitly use LangGraph (newer approach)
langgraph_agent = langchain_adapter.create_agent(
    tools=tools,
    llm=llm,
    system_message="You are a helpful assistant with access to Arc Memory.",
    verbose=True,
    use_langgraph=True  # Explicitly use LangGraph
)

# Explicitly use legacy AgentExecutor
legacy_agent = langchain_adapter.create_agent(
    tools=tools,
    llm=llm,
    system_message="You are a helpful assistant with access to Arc Memory.",
    verbose=True,
    use_langgraph=False  # Explicitly use legacy AgentExecutor
)

# Error handling for LangChain integration
try:
    response = agent.invoke({"input": "What's the decision trail for src/auth/login.py line 42?"})
    print(response)
except Exception as e:
    print(f"Error using LangChain agent: {e}")
    # Try with different model
    llm = ChatOpenAI(model="gpt-3.5-turbo")
    agent = langchain_adapter.create_agent(
        tools=tools,
        llm=llm,
        system_message="You are a helpful assistant with access to Arc Memory."
    )
    response = agent.invoke({"input": "What's the decision trail for src/auth/login.py line 42?"})
    print(response)
```

### OpenAI Integration

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

# Use the agent with a simple query
response = agent("What's the decision trail for src/auth/login.py line 42?")
print(response)

# Use the agent with structured messages
messages = [
    {"role": "system", "content": "You are a helpful assistant with access to Arc Memory."},
    {"role": "user", "content": "What's the decision trail for src/auth/login.py line 42?"}
]
response = agent(messages)
print(response)

# Using streaming responses
agent_stream = openai_adapter.create_agent(
    tools=tools,
    model="gpt-4o",
    temperature=0,
    system_message="You are a helpful assistant with access to Arc Memory.",
    stream=True
)

# Process streaming response
try:
    for chunk in agent_stream("What's the decision trail for src/auth/login.py line 42?"):
        if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
            content = chunk.choices[0].delta.content
            if content:
                print(content, end="", flush=True)
    print()  # Add a newline at the end
except Exception as e:
    print(f"Error during streaming: {e}")

# Advanced streaming with stream_options
agent_stream_advanced = openai_adapter.create_agent(
    tools=tools,
    model="gpt-4o",
    temperature=0,
    system_message="You are a helpful assistant with access to Arc Memory.",
    stream=True,
    stream_options={"include_usage": True}  # Include token usage in the response
)

# Process advanced streaming response
try:
    for chunk in agent_stream_advanced("What's the decision trail for src/auth/login.py line 42?"):
        if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
            content = chunk.choices[0].delta.content
            if content:
                print(content, end="", flush=True)
        # Check for usage information in the final chunk
        if hasattr(chunk, 'usage') and chunk.usage:
            print(f"\nToken usage: {chunk.usage}")
    print()  # Add a newline at the end
except Exception as e:
    print(f"Error during streaming: {e}")

# Error handling for OpenAI integration
try:
    response = agent("What's the decision trail for src/auth/login.py line 42?")
    print(response)
except Exception as e:
    print(f"Error using OpenAI agent: {e}")
    # Try with different model
    fallback_agent = openai_adapter.create_agent(
        tools=tools,
        model="gpt-3.5-turbo",
        temperature=0,
        system_message="You are a helpful assistant with access to Arc Memory."
    )
    response = fallback_agent("What's the decision trail for src/auth/login.py line 42?")
    print(f"Fallback response: {response}")

# Create an OpenAI Assistant
assistant = openai_adapter.create_assistant(
    tools=tools,
    name="Arc Memory Assistant",
    instructions="You are a helpful assistant with access to Arc Memory.",
    model="gpt-4o"
)
print(f"Assistant created: {assistant.id}")

# Create a thread and run the assistant
from openai import OpenAI
client = OpenAI()

thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="What's the decision trail for src/auth/login.py line 42?"
)

run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
)

# In a real application, you would poll for completion
import time
while run.status in ["queued", "in_progress"]:
    time.sleep(1)
    run = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )

# Get the assistant's response
messages = client.beta.threads.messages.list(
    thread_id=thread.id
)
for message in messages.data:
    if message.role == "assistant":
        print(f"Assistant: {message.content[0].text.value}")
```

## Advanced Use Cases

### Building a Custom Agent

```python
from arc_memory import Arc
from arc_memory.sdk.errors import AdapterNotFoundError, FrameworkError

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Define the functions you want to expose to the agent
functions = [
    arc.query,
    arc.get_decision_trail,
    arc.get_related_entities,
    arc.get_entity_details,
    arc.analyze_component_impact
]

# Function to create an agent with error handling
def create_agent_with_framework(framework_name):
    try:
        # Get the adapter for the framework
        from arc_memory.sdk.adapters import get_adapter
        adapter = get_adapter(framework_name)

        # Adapt the functions to the framework
        tools = adapter.adapt_functions(functions)

        # Create an agent with the adapted tools
        if framework_name == "openai":
            agent = adapter.create_agent(
                tools=tools,
                model="gpt-4o",
                system_message="You are a helpful assistant with access to Arc Memory."
            )
            return agent

        elif framework_name == "langchain":
            from langchain_openai import ChatOpenAI

            agent = adapter.create_agent(
                tools=tools,
                llm=ChatOpenAI(model="gpt-4o"),
                system_message="You are a helpful assistant with access to Arc Memory."
            )
            return agent

    except AdapterNotFoundError:
        print(f"Adapter not found for framework: {framework_name}")
        # List available adapters
        from arc_memory.sdk.adapters import get_adapter_names
        print(f"Available adapters: {get_adapter_names()}")
        return None

    except FrameworkError as e:
        print(f"Framework error: {e}")
        return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Try to create an OpenAI agent
openai_agent = create_agent_with_framework("openai")
if openai_agent:
    try:
        response = openai_agent("What's the decision trail for src/auth/login.py line 42?")
        print(f"OpenAI Agent Response: {response}")
    except Exception as e:
        print(f"Error using OpenAI agent: {e}")

# Try to create a LangChain agent
langchain_agent = create_agent_with_framework("langchain")
if langchain_agent:
    try:
        response = langchain_agent.invoke({"input": "What's the decision trail for src/auth/login.py line 42?"})
        print(f"LangChain Agent Response: {response}")
    except Exception as e:
        print(f"Error using LangChain agent: {e}")

# Example of registering a custom adapter
from arc_memory.sdk.adapters import register_adapter
from arc_memory.sdk.adapters.base import FrameworkAdapter

class CustomAdapter(FrameworkAdapter):
    def get_name(self):
        return "custom"

    def get_version(self):
        return "1.0.0"

    def get_framework_name(self):
        return "custom_framework"

    def get_framework_version(self):
        return "1.0.0"

    def adapt_functions(self, functions):
        # Convert Arc Memory functions to custom framework tools
        return [{"name": func.__name__, "function": func} for func in functions]

    def create_agent(self, **kwargs):
        # Create a simple agent that calls the functions directly
        tools = kwargs.get("tools", [])

        def agent(query):
            # This is a very simple agent implementation
            if "decision trail" in query.lower():
                for tool in tools:
                    if tool["name"] == "get_decision_trail":
                        return tool["function"]("src/auth/login.py", 42)
            return "I don't know how to answer that question."

        return agent

# Register the custom adapter
try:
    register_adapter(CustomAdapter())
    custom_agent = create_agent_with_framework("custom")
    if custom_agent:
        response = custom_agent("What's the decision trail for src/auth/login.py line 42?")
        print(f"Custom Agent Response: {response}")
except Exception as e:
    print(f"Error registering custom adapter: {e}")
```
