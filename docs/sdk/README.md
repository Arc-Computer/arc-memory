# Arc Memory SDK

The Arc Memory SDK provides a framework-agnostic interface for interacting with a knowledge graph built from your code repositories and related data sources. Use it directly in your applications or integrate it with agent frameworks like LangChain and OpenAI.

> **New to Arc Memory?** Check out our [Quickstart Guide](../quickstart.md) to get up and running in under 30 minutes.

## Overview

Arc Memory builds a local, bi-temporal knowledge graph from Git repositories, GitHub issues/PRs, and ADRs. This SDK lets you query this graph to understand code history, relationships, and potential impacts of changes.

Key features:
- **Natural language queries** about the codebase
- **Decision trail analysis** for understanding why code exists
- **Entity relationship exploration** for discovering connections
- **Component impact analysis** for predicting blast radius
- **Temporal analysis** for understanding how code evolves over time
- **Framework adapters** for integration with LangChain, OpenAI, and other agent frameworks

## Installation

```bash
pip install arc-memory
```

### Optional Dependencies

```bash
# Install with GitHub integration
pip install arc-memory[github]

# Install with Linear integration
pip install arc-memory[linear]

# Install with LLM enhancement capabilities
pip install arc-memory[llm]

# Install with all optional dependencies
pip install arc-memory[all]
```

## Authentication

Arc Memory supports authentication with GitHub and Linear for accessing private repositories and issues.

### GitHub Authentication

```python
from arc_memory.auth.github import authenticate_github

# Authenticate with GitHub using device flow
token = authenticate_github()
print(f"Successfully authenticated with GitHub: {token[:5]}...")

# Store the token in environment variables
import os
os.environ["GITHUB_TOKEN"] = token

# Now you can use Arc with GitHub integration
from arc_memory import Arc
arc = Arc(repo_path="./")
```

### Linear Authentication

```python
from arc_memory.auth.linear import authenticate_linear

# Authenticate with Linear using OAuth
token = authenticate_linear()
print(f"Successfully authenticated with Linear: {token[:5]}...")

# Store the token in environment variables
import os
os.environ["LINEAR_API_KEY"] = token

# Now you can use Arc with Linear integration
from arc_memory import Arc
arc = Arc(repo_path="./")
```

## Quick Start

```python
from arc_memory import Arc

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Query the knowledge graph
result = arc.query("Why was the authentication system refactored?")
print(result.answer)

# Get the decision trail for a specific line in a file
decision_trail = arc.get_decision_trail("src/auth/login.py", 42)
for entry in decision_trail:
    print(f"{entry.title}: {entry.rationale}")

# Get entities related to a specific entity
related = arc.get_related_entities("commit:abc123")
for entity in related:
    print(f"{entity.title} ({entity.relationship})")

# Analyze the potential impact of changes to a component
impact = arc.analyze_component_impact("file:src/auth/login.py")
for component in impact:
    print(f"{component.title}: {component.impact_score}")

# Export the knowledge graph
export_result = arc.export_graph("knowledge_graph.json")
print(f"Exported {export_result.entity_count} entities and {export_result.relationship_count} relationships")
```

## Framework Integration

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

# Create a LangChain agent with Arc Memory tools
llm = ChatOpenAI(model="gpt-4o")
agent = langchain_adapter.create_agent(tools=tools, llm=llm)

# Use the agent
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
agent = openai_adapter.create_agent(tools=tools, model="gpt-4o")

# Use the agent
response = agent("What's the decision trail for src/auth/login.py line 42?")
print(response)

# Or create an OpenAI Assistant
assistant = openai_adapter.create_assistant(
    tools=tools,
    name="Arc Memory Assistant",
    instructions="You are a helpful assistant with access to Arc Memory."
)
```

## Core Concepts

### Knowledge Graph

Arc Memory builds a knowledge graph from various sources, including:
- Git repositories (commits, branches, tags)
- GitHub (issues, pull requests, comments)
- ADRs (Architectural Decision Records)
- Linear (issues, projects, teams)
- Custom data sources via plugins

The knowledge graph consists of nodes (entities) and edges (relationships) that capture the causal connections between decisions, implications, and code changes.

### Bi-Temporal Data Model

Arc Memory's bi-temporal data model tracks both:
- **Valid time**: When something happened in the real world
- **Transaction time**: When it was recorded in the system

This enables powerful temporal queries that can answer questions like "What did we know about X at time Y?" and "How has X evolved over time?"

### Causal Relationships

Arc Memory captures causal relationships between entities, such as:
- Decision > Implication > Code Change
- Issue > PR > Commit > File
- ADR > Implementation > Test

These causal relationships enable powerful reasoning about why code exists and how it relates to business decisions.

## Next Steps

- [Getting Started Guide](../getting_started.md)
- [SDK Examples](../examples/sdk_examples.md)
- [API Reference](./api_reference.md)
- [Framework Adapters](./adapters.md)
