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

Arc Memory supports authentication with various data sources. Configuration is primarily via environment variables, especially for initial token acquisition. Refer to specific guides for detailed setup.

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
# arc = Arc(repo_path="./") # Assuming GITHUB_TOKEN is set
```
For detailed setup, see the [GitHub Integration Guide](../guides/github_integration.md).

### Jira Authentication
Jira integration **requires you to create your own Jira OAuth 2.0 Application** and set the following environment variables:
- `ARC_JIRA_CLIENT_ID`
- `ARC_JIRA_CLIENT_SECRET`
- `ARC_JIRA_REDIRECT_URI`
- `ARC_JIRA_CLOUD_ID` (can sometimes be auto-detected by `arc auth jira`)

Run `arc auth jira` via the CLI to authenticate. Arc Memory will store the tokens.
For complete instructions, see the [Jira Integration Guide](../guides/jira_integration.md).

### Notion Authentication
Notion integration requires a user-configured setup:
- **Internal Integration Token (Recommended)**: Create an internal integration in Notion, get the token, and set it as the `NOTION_API_KEY` environment variable.
- **Public OAuth App**: If you have your own Public Notion OAuth app, set `ARC_NOTION_CLIENT_ID`, `ARC_NOTION_CLIENT_SECRET`, and `ARC_NOTION_REDIRECT_URI`, then run `arc auth notion`.

**Crucially, you must share specific Notion pages and databases with your integration.**
For full details, refer to the [Notion Integration Guide](../guides/notion_integration.md).

### Linear Authentication

```python
from arc_memory.auth.linear import authenticate_linear

# Authenticate with Linear using OAuth
# token = authenticate_linear() # This will open a browser for OAuth
# print(f"Successfully authenticated with Linear: {token[:5]}...")

# Store the token in environment variables (or let Arc Memory handle it via keyring after CLI auth)
import os
# os.environ["LINEAR_API_KEY"] = token 

# Now you can use Arc with Linear integration
from arc_memory import Arc
# arc = Arc(repo_path="./") # Assuming LINEAR_API_KEY is set or token is in keyring
```
The easiest way is to use `arc auth linear` from the CLI. For details, see the [Linear Integration Guide](../guides/linear_integration.md).


## Quick Start

### Building the Knowledge Graph
First, build the knowledge graph for your repository.
```python
from arc_memory import Arc

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Build the graph (this example assumes GitHub, Jira, and Notion might be used)
# Ensure relevant auth environment variables are set (e.g., GITHUB_TOKEN, NOTION_API_KEY)
# and you've run `arc auth jira` if using Jira.
build_summary = arc.build(
    include_github=True,
    # include_jira=True, # Uncomment if Jira is configured
    # include_notion=True, # Uncomment if Notion is configured
    source_configs={
        "jira": {
            # cloud_id might be needed if ARC_JIRA_CLOUD_ID env var is not set
            # "cloud_id": "your-jira-cloud-id", 
            "project_keys": ["YOUR_PROJECT_KEY"] # Example: only ingest this Jira project
        },
        "notion": {
            "database_ids": ["your_notion_database_id"], # Example: ingest this specific database
            "page_ids": ["your_notion_page_id"] # Example: ingest this specific page
        }
    },
    verbose=True
)

print("Build complete. Summary of ingestors:")
for summary in build_summary.get("ingestor_summary", []):
    status_line = f"  - Ingestor: {summary['name']}, Status: {summary['status']}"
    status_line += f", Nodes: {summary['nodes_processed']}, Edges: {summary['edges_processed']}"
    if summary['status'] == 'failure' and summary.get('error_message'):
        status_line += f", Error: {summary['error_message']}"
    print(status_line)

# You can inspect other parts of build_summary like:
# print(f"Total nodes added: {build_summary.get('total_nodes_added')}")
# print(f"Total edges added: {build_summary.get('total_edges_added')}")
```

### Querying and Analyzing
Once the graph is built:
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

# Export the knowledge graph for a specific PR (example)
# export_result = arc.export_graph(pr_sha="commit_sha_of_pr_head", output_path="knowledge_graph_pr.json")
# print(f"Exported {export_result.get('entity_count',0)} entities and {export_result.get('relationship_count',0)} relationships")
```

## Advanced Configuration and Build Results

### Configuring Ingestors with `source_configs`

The `arc.build()` method accepts a `source_configs` parameter. This is a dictionary where keys are ingestor names (e.g., `"jira"`, `"notion"`, `"github"`, or custom ingestor names) and values are dictionaries containing specific configurations for that ingestor.

```python
build_summary = arc.build(
    # ... other parameters ...
    source_configs={
        "jira": {
            "cloud_id": "your-jira-cloud-id", # Overrides ARC_JIRA_CLOUD_ID env var for this build
            "project_keys": ["PROJ_A", "PROJ_B"], # Ingest only these projects
            # Add other Jira-specific configs here if supported by the ingestor
        },
        "notion": {
            "database_ids": ["notion_db_id_1", "notion_db_id_2"], # Ingest these specific databases
            "page_ids": ["notion_page_id_1"], # Ingest this specific page
            # Add other Notion-specific configs here
        },
        "github": {
            "include_issues": True,
            "include_prs": True,
            # "max_items_per_type": 100 # Example of a hypothetical future config
        }
        # "your_custom_ingestor_name": {
        #     "custom_param": "value"
        # }
    }
)
```

This allows for fine-grained control over data ingestion without relying solely on global settings or environment variables for every aspect.

### Understanding Build Results with `ingestor_summary`

The dictionary returned by `arc.build()` (referred to as `build_summary` in examples) contains valuable information about the build process. A key part of this is the `ingestor_summary` list.

Each item in `ingestor_summary` is a dictionary detailing the outcome for a specific data ingestor:
- **`name`**: The name of the ingestor (e.g., `"git"`, `"github"`, `"jira"`).
- **`status`**: `"success"` or `"failure"`.
- **`nodes_processed`**: Number of nodes generated by this ingestor (0 if failed).
- **`edges_processed`**: Number of edges generated by this ingestor (0 if failed).
- **`error_message`**: A string with the error message if `status` is `"failure"`, otherwise `None`.
- **`processing_time_seconds`**: Time taken by this ingestor.
- **`metadata`**: (For some ingestors, like Notion) A sub-dictionary with specific counts, e.g., `{"page_count": X, "database_count": Y}`.

Inspecting `ingestor_summary` is highly recommended to verify that each data source was processed as expected and to diagnose any issues. The `total_nodes_added` and `total_edges_added` fields in the main build summary reflect the sum from *successful* ingestors.

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

## Writing to the Graph

Agents can also **persist new knowledge** into Arc Memory. Create `Node` and
`Edge` instances from `arc_memory.schema.models` and pass them to
`arc.add_nodes_and_edges()`:

```python
from arc_memory import Arc
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel

arc = Arc(repo_path="./")

doc = Node(
    id="document:agent-note",
    type=NodeType.DOCUMENT,
    title="Agent Observation",
    body="This was learned by the agent."
)

link = Edge(src=doc.id, dst="commit:abc123", rel=EdgeRel.REFERENCES)

arc.add_nodes_and_edges([doc], [link])
```

This uses the same transactional write path as Arc's build process. SQLite is
the default backend, so coordinate concurrent writes or use Neo4j if you need
higher write throughput.

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
- [How to Create a Custom Data Ingestor](../guides/custom_ingestors.md) - Extend Arc Memory with your own data sources.
