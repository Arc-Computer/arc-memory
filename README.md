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

## What The Arc SDK Does

1. **Record the why.**
   Arc's Temporal Knowledge Graph ingests commits, PRs, issues, and ADRs to preserve architectural intent and decision history—entirely on your machine.

2. **Model the system.**
   From that history Arc derives a **causal graph** of services, data flows, and constraints—a lightweight world-model that stays in sync with the codebase.

3. **Capture causal relationships.**
   Arc tracks decision → implication → code-change chains, enabling multi-hop reasoning to show why decisions were made and their predicted impact.

4. **Enhance PR reviews.**
   Arc's GitHub Actions integration surfaces decision trails and blast-radius hints directly in PR comments, giving reviewers instant context before they hit "Approve."

## How Arc Memory Differs

Arc Memory takes a fundamentally different approach from traditional code analysis tools:

### Temporal Understanding
Unlike static code analysis tools, Arc captures why code evolved the way it did, preserving institutional knowledge even as teams change. The bi-temporal knowledge graph tracks not just what changed, but the reasoning and decisions behind those changes across time.

### Predictive Insights
Arc predicts the blast radius of code modifications before you merge, reducing incidents and regressions. By analyzing the causal relationships between components, Arc can identify which parts of your system might be affected by a change, helping you make more informed decisions.

### Agent-Ready Architecture
Arc's knowledge graph powers intelligent agents that can review code with historical context, navigate incidents with causal understanding, and implement self-healing improvements. The framework-agnostic design treats agent interactions as function calls for maximum composability, allowing integration with any agent framework.

## Quick Start

```bash
# Install Arc Memory
pip install arc-memory[github]

# Build a knowledge graph from your repository
cd /path/to/your/repo
arc build --github
```

Check out the [example agents](./docs/examples/agents/) and [demo applications](./demo/) to see Arc Memory in action.

## Core Features

### Knowledge Graph

```bash
# Build with GitHub and Linear data
arc build --github --linear
```

### Decision Trails

```bash
# Show decision trail for a specific file and line
arc why file path/to/file.py 42

# Ask natural language questions
arc why query "What decision led to using SQLite instead of PostgreSQL?"
```

### GitHub Actions Integration

```bash
# Export knowledge graph for GitHub Actions
arc export <commit-sha> export.json --compress
```

## SDK for Developers

```python
from arc_memory import Arc

# Initialize Arc with your repository path
arc = Arc(repo_path="./")

# Ask a question about your codebase
result = arc.query("What were the major changes in the last release?")
print(f"Answer: {result.answer}")

# Find out why a specific piece of code exists
decision_trail = arc.get_decision_trail("src/auth/login.py", 42)
```

## Documentation

- [Getting Started Guide](./docs/getting_started.md) - Complete setup instructions
- [SDK Documentation](./docs/sdk/README.md) - Using the Arc Memory SDK
- [CLI Reference](./docs/cli/README.md) - Command-line interface details
- [Examples](./docs/examples/README.md) - Real-world usage examples

## Why It Matters

- **Faster onboarding** for new team members
- **Reduced knowledge loss** when developers leave
- **More efficient code reviews** with contextual insights
- **Safer refactoring** with impact prediction
- **Better agent coordination** through shared memory

## SDK for Developers and Agents

Arc Memory provides a clean, Pythonic SDK that enables both developers and AI agents to programmatically access the knowledge graph:

```python
from arc_memory import Arc

# Initialize Arc with your repository path
arc = Arc(repo_path="./")

# Ask a question about your codebase
result = arc.query("What were the major changes in the last release?")
print(f"Answer: {result.answer}")

# Find out why a specific piece of code exists
decision_trail = arc.get_decision_trail("src/core/auth.py", 42)
for entry in decision_trail:
    print(f"Decision: {entry.title}")
    print(f"Rationale: {entry.rationale}")

# Analyze the potential impact of a change
impact = arc.analyze_component_impact("file:src/api/endpoints.py")
for component in impact:
    print(f"Affected: {component.title} (Impact score: {component.impact_score})")
```

The SDK follows a framework-agnostic design with adapters for popular frameworks like LangChain and OpenAI, making it easy to integrate Arc Memory into your development workflows or AI applications.

## Privacy

Telemetry is disabled by default. Arc Memory respects your privacy and will only collect anonymous usage data if you explicitly opt in.

## License

MIT
