# Arc: The Memory Layer for Engineering Teams

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

*Arc is the memory layer for engineering teams — it records **why** every change was made, predicts the blast-radius of new code before you merge, and feeds that context to agents so they can handle long-range refactors safely.*

## What Arc Memory Does

Arc Memory provides a complete solution for preserving and leveraging engineering knowledge:

1. **Records the why behind code changes**
   Ingests commits, PRs, issues, and ADRs to preserve architectural intent and decision history.

2. **Models your system as a temporal knowledge graph**
   Creates a causal graph of code entities, services, and their relationships that evolves with your codebase.

3. **Enables powerful temporal reasoning**
   Tracks decision → implication → code-change chains to show why decisions were made and predict their impact.

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
arc build --github --linear --llm-enhancement standard --llm-provider openai --llm-model o4-mini
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
- **Explanation**: [Architecture Overview](./docs/architecture.md) - Concepts and design
- **Reference**: [SDK API](./docs/sdk/README.md), [CLI Commands](./docs/cli/README.md), and [Multi-Repository Support](./docs/multi_repository.md)

## Why It Matters

- **Faster onboarding** for new team members
- **Reduced knowledge loss** when developers leave
- **More efficient code reviews** with contextual insights
- **Safer refactoring** with impact prediction
- **Better agent coordination** through shared memory

## Architecture

Arc Memory is built around a bi-temporal knowledge graph that captures:

- **Code Structure**: Files, functions, classes, and their relationships
- **Version History**: Commits, PRs, issues, and their temporal connections
- **Decision Context**: ADRs, discussions, and rationales behind changes
- **Causal Relationships**: How changes in one component affect others
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
