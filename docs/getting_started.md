# Getting Started with Arc Memory

This guide will help you get started with Arc Memory, from installation to building your first knowledge graph and querying it with the SDK.

## Installation

Install Arc Memory using pip:

```bash
pip install arc-memory
```

For development or to include optional dependencies:

```bash
# Install with all optional dependencies
pip install arc-memory[all]

# Install with specific optional dependencies
pip install arc-memory[github,linear,neo4j]
```

## Building Your First Knowledge Graph

Before you can use the SDK, you need to build a knowledge graph from your repository. This is a critical first step - the knowledge graph is the foundation that powers all of Arc Memory's capabilities.

### Using the CLI to Build the Graph

The easiest way to build your knowledge graph is using the CLI:

```bash
# Navigate to your repository
cd /path/to/your/repo

# Build the knowledge graph
arc build
```

This will:
1. Analyze your Git repository
2. Extract commits, branches, and tags
3. Process GitHub issues and PRs (if GitHub integration is configured)
4. Extract ADRs (if present in the repository)
5. Build a knowledge graph in a local SQLite database (stored in `~/.arc/db.sqlite` by default)

### Building Options

You can customize the build process with various options:

```bash
# Build with verbose output
arc build --verbose

# Build with a specific branch
arc build --branch main

# Build with a specific commit range
arc build --since 2023-01-01

# Build with a specific number of commits
arc build --limit 100

# Build with a specific database path
arc build --db-path /path/to/custom/db.sqlite
```

### Programmatically Building the Graph

You can also build the knowledge graph programmatically using the SDK:

```python
from arc_memory import Arc
from arc_memory.auto_refresh import refresh_knowledge_graph

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Build or refresh the knowledge graph
refresh_result = refresh_knowledge_graph(
    repo_path="./",
    include_github=True,
    include_linear=False,
    verbose=True
)

print(f"Added {refresh_result.nodes_added} nodes and {refresh_result.edges_added} edges")
print(f"Updated {refresh_result.nodes_updated} nodes and {refresh_result.edges_updated} edges")
```

### Verifying the Build

To verify that your knowledge graph was built successfully:

```bash
# Check the graph statistics
arc stats

# Or programmatically
from arc_memory import Arc

arc = Arc(repo_path="./")
node_count = arc.get_node_count()
edge_count = arc.get_edge_count()

print(f"Knowledge graph contains {node_count} nodes and {edge_count} edges")

### Configuring Data Sources

#### GitHub Integration

To include GitHub issues and PRs in your knowledge graph:

```bash
# Authenticate with GitHub
arc auth github

# Build with GitHub data
arc build --github
```

#### Linear Integration

To include Linear issues and projects:

```bash
# Authenticate with Linear
arc auth linear

# Build with Linear data
arc build --linear
```

#### ADR Integration

Arc Memory automatically detects and processes ADRs in your repository. By default, it looks for files matching these patterns:
- `docs/adr/*.md`
- `docs/adrs/*.md`
- `doc/adr/*.md`
- `doc/adrs/*.md`
- `ADR-*.md`
- `ADR_*.md`

## Using the SDK

Once you've built a knowledge graph, you can use the SDK to query it:

```python
from arc_memory import Arc

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Query the knowledge graph
result = arc.query("Why was the authentication system refactored?")
print(result.answer)
```

### Core SDK Methods

#### Natural Language Queries

```python
# Query the knowledge graph
result = arc.query(
    question="Why was the authentication system refactored?",
    max_results=5,
    max_hops=3,
    include_causal=True
)

print(f"Answer: {result.answer}")
print(f"Confidence: {result.confidence}")
print("Evidence:")
for evidence in result.evidence:
    print(f"- {evidence['title']}")
```

#### Decision Trail Analysis

```python
# Get the decision trail for a specific line in a file
decision_trail = arc.get_decision_trail(
    file_path="src/auth/login.py",
    line_number=42,
    max_results=5,
    include_rationale=True
)

for entry in decision_trail:
    print(f"{entry.title}: {entry.rationale}")
    print(f"Importance: {entry.importance}")
    print(f"Position: {entry.trail_position}")
    print("---")
```

#### Entity Relationship Exploration

```python
# Get entities related to a specific entity
related = arc.get_related_entities(
    entity_id="commit:abc123",
    relationship_types=["DEPENDS_ON", "IMPLEMENTS"],
    direction="both",
    max_results=10
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
print("Related Entities:")
for related in entity.related_entities:
    print(f"- {related.title} ({related.relationship})")
```

#### Component Impact Analysis

```python
# Analyze the potential impact of changes to a component
impact = arc.analyze_component_impact(
    component_id="file:src/auth/login.py",
    impact_types=["direct", "indirect", "potential"],
    max_depth=3
)

for component in impact:
    print(f"{component.title}: {component.impact_score}")
    print(f"Impact Type: {component.impact_type}")
    print(f"Impact Path: {' -> '.join(component.impact_path)}")
    print("---")
```

#### Temporal Analysis

```python
# Get the history of an entity over time
history = arc.get_entity_history(
    entity_id="file:src/auth/login.py",
    start_date="2023-01-01",
    end_date="2023-12-31",
    include_related=True
)

for entry in history:
    print(f"{entry.timestamp}: {entry.title}")
    print(f"Change Type: {entry.change_type}")
    print(f"Previous Version: {entry.previous_version}")
    print("---")
```

#### Exporting the Knowledge Graph

```python
# Export the knowledge graph
export_result = arc.export_graph(
    output_path="knowledge_graph.json",
    pr_sha="abc123",  # Optional: Filter by PR
    entity_types=["COMMIT", "PR", "ISSUE"],  # Optional: Filter by entity type
    start_date="2023-01-01",  # Optional: Filter by date
    end_date="2023-12-31",  # Optional: Filter by date
    format="json",
    compress=True,
    optimize_for_llm=True
)

print(f"Exported {export_result.entity_count} entities and {export_result.relationship_count} relationships")
print(f"Output path: {export_result.output_path}")
```

## Next Steps

- [SDK Examples](./examples/sdk_examples.md) - More detailed examples of using the SDK
- [Framework Adapters](./sdk/adapters.md) - Integrating with agent frameworks
- [CLI Reference](./cli/build.md) - Using the Arc Memory CLI
- [API Reference](./sdk/api_reference.md) - Detailed API documentation
