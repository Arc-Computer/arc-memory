# Arc Memory: The Memory Layer for Engineering Teams

<p align="center">
  <img src="public/Arc SDK Header.png" alt="Arc Logo"/>
</p>

<p align="center">
  <a href="https://www.arc.computer"><img src="https://img.shields.io/badge/website-arc.computer-blue" alt="Website"/></a>
  <a href="https://github.com/Arc-Computer/arc-memory/actions"><img src="https://img.shields.io/badge/tests-passing-brightgreen" alt="Tests"/></a>
  <a href="https://pypi.org/project/arc-memory/"><img src="https://img.shields.io/pypi/v/arc-memory" alt="PyPI"/></a>
  <a href="https://pypi.org/project/arc-memory/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="Python"/></a>
  <a href="https://github.com/Arc-Computer/arc-memory/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Arc-Computer/arc-memory" alt="License"/></a>
  <a href="https://docs.arc.computer"><img src="https://img.shields.io/badge/docs-mintlify-teal" alt="Documentation"/></a>
</p>

*Arc Memory preserves the **why** behind code changes, predicts impact before you merge, and provides the context developers and AI agents need to work with complex codebases safely and efficiently.*

## Why Arc Memory Exists

Every engineering team faces these challenges:

1. **Lost Context**: "Why was this code written this way?" becomes impossible to answer when the original developers leave
2. **Risky Changes**: Even small changes can have unexpected ripple effects across repositories
3. **Knowledge Silos**: Critical information gets scattered across Git, PRs, issues, and documentation
4. **Slow Onboarding**: New team members spend weeks piecing together how systems work and why decisions were made

Arc Memory solves these problems by creating a unified memory layer that captures, preserves, and makes accessible the complete context behind your code.

## What Makes Arc Memory Different

Arc Memory goes beyond traditional tools by:

1. **Preserving Complete Context**
   Connects code changes to the decisions, discussions, and requirements that drove them, creating a complete picture that survives team turnover.

2. **Working Across Repository Boundaries**
   Builds a unified view across your entire system, revealing dependencies and relationships that would otherwise remain hidden.

3. **Enabling Time-Travel Understanding**
   Reconstructs what was known at any point in time, helping you understand why decisions made sense with the information available then.

## What Arc Memory Does

Arc Memory provides a complete solution for preserving and leveraging engineering knowledge:

1. **Records the why behind code changes**
   Ingests commits, PRs, issues, and ADRs to preserve architectural intent and decision history.

2. **Models your system as a bi-temporal knowledge graph**
   Creates a causal graph of code entities, services, and their relationships that evolves with your codebase, tracking both valid time and transaction time.

3. **Enables powerful temporal reasoning**
   Answers questions like "What did we know about X at time Y?" and "How has our understanding of Z evolved over time?"

4. **Analyzes across multiple repositories**
   Builds a unified knowledge graph across multiple repositories to understand cross-repository dependencies and relationships.

5. **Enhances developer workflows**
   Surfaces decision trails and blast-radius predictions in PR reviews and provides context to AI agents.

## Quick Start

```bash
# Install Arc Memory with all dependencies
pip install arc-memory[all]

# Authenticate with GitHub
arc auth github

# Build a knowledge graph with LLM enhancement
cd /path/to/your/repo
arc build --github --llm-enhancement standard --llm-provider openai --llm-model o4-mini
```

Check out our [Code Time Machine demo](./demo/code_time_machine/) to explore file evolution, decision trails, and impact prediction, or browse other [example agents](./docs/examples/agents/) and [demo applications](./demo/).

## Core Features

### Powerful CLI Tools

```bash
# Explore decision trails for specific code
arc why file path/to/file.py 42

# Ask natural language questions about your codebase
arc why query "What decision led to using SQLite instead of PostgreSQL?"

# Run the Code Time Machine demo
./demo/code_time_machine/run_demo.sh path/to/file.py

# Export knowledge graph for CI/CD integration
arc export <commit-sha> export.json --compress
```

## SDK for Developers and Agents

Arc Memory provides a clean, Pythonic SDK for accessing and analyzing your codebase's knowledge graph:

```python
from arc_memory.sdk import Arc

# Initialize Arc with your repository path
arc = Arc(repo_path="./")

# Ask natural language questions about your codebase
result = arc.query("What were the major changes in the last release?")
print(f"Answer: {result.answer}")

# Get file history and evolution
file_history = arc.get_file_history("arc_memory/sdk/core.py")
for entry in file_history:
    print(f"{entry.timestamp}: {entry.author} - {entry.change_type}")

# Find decision trails with rationales
decision_trail = arc.get_decision_trail("arc_memory/sdk/core.py", 42)
for entry in decision_trail:
    print(f"Decision: {entry.title}")
    print(f"Rationale: {entry.rationale}")

# Analyze potential impact of changes
impact = arc.analyze_component_impact("file:arc_memory/sdk/core.py")
for component in impact:
    print(f"Affected: {component.title} (Impact: {component.impact_score})")
```

## Documentation

Following the [Diataxis](https://diataxis.fr/) framework:

- **Tutorials**: [Getting Started Guide](./docs/getting_started.md) - Step-by-step introduction
- **How-to Guides**: [Code Time Machine Demo](./demo/code_time_machine/) - Task-oriented examples
- **Explanation**:
  - [Architecture Overview](./docs/architecture.md) - System design and components
  - [Temporal Understanding](./docs/temporal_understanding.md) - Bi-temporal model explained
  - [Framework Integration](./docs/framework_integration.md) - Using with agent frameworks
- **Reference**: [SDK API](./docs/sdk/README.md), [CLI Commands](./docs/cli/README.md), and [Multi-Repository Support](./docs/multi_repository.md)

## Why It Matters

- **Preserve decision context** that Git history alone can't capture
- **Understand code evolution** with complete temporal context
- **Predict change impact** across repository boundaries
- **Accelerate onboarding** by revealing the "why" behind code
- **Enable safer refactoring** with comprehensive impact analysis
- **Power intelligent agents** with deep contextual understanding

## Architecture

Arc Memory is built around a bi-temporal knowledge graph that captures:

- **Code Structure**: Files, functions, classes, and their relationships
- **Version History**: Commits, PRs, issues, and their temporal connections
- **Decision Context**: ADRs, discussions, and rationales behind changes
- **Causal Relationships**: How changes in one component affect others
- **Temporal Dimensions**: Both when things happened and when they were recorded
- **Multi-Repository Support**: Analyze and query across multiple repositories

This architecture enables powerful temporal reasoning and impact prediction capabilities that traditional code analysis tools cannot provide.

### Multi-Repository Support

Arc Memory supports analyzing multiple repositories within a single knowledge graph:

```python
from arc_memory.sdk import Arc

# Initialize with your primary repository
arc = Arc(repo_path="./main-repo")

# Add additional repositories
repo2_id = arc.add_repository("./service-repo", name="Service Repository")
repo3_id = arc.add_repository("./frontend-repo", name="Frontend Repository")

# List all repositories in the knowledge graph
repos = arc.list_repositories()
for repo in repos:
    print(f"{repo['name']} ({repo['id']})")

# Set active repositories for queries
arc.set_active_repositories([repo2_id, repo3_id])

# Query across specific repositories
result = arc.query("How do the frontend and service components interact?")
```

The SDK follows a framework-agnostic design with adapters for popular frameworks like LangChain and OpenAI, making it easy to integrate Arc Memory into your development workflows or AI applications.

## Privacy and License

Telemetry is disabled by default. Arc Memory respects your privacy and will only collect anonymous usage data if you explicitly opt in.

Licensed under MIT.
