# Arc Memory: The Memory Layer for Engineering Teams

<p align="center">
  <img src="public/arc_logo.png" alt="Arc Logo" width="200"/>
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

## What Arc Actually Does

1. **Record the why.**
   Arc's Temporal Knowledge Graph ingests commits, PRs, issues, and ADRs to preserve architectural intent and decision history—entirely on your machine.

2. **Model the system.**
   From that history Arc derives a **causal graph** of services, data flows, and constraints—a lightweight world-model that stays in sync with the codebase.

3. **Capture causal relationships.**
   Arc tracks decision → implication → code-change chains, enabling multi-hop reasoning to show why decisions were made and their predicted impact.

4. **Enhance PR reviews.**
   Arc's GitHub extension surfaces decision trails and blast-radius hints directly in the PR view, giving reviewers instant context before they hit "Approve."

## Why It Matters

As AI generates exponentially more code, the critical bottleneck shifts from *generation* to *understanding, provenance, and coordination*:

* **Preserve the "why" behind changes.** When a senior engineer leaves, their rationale often vanishes. Arc ensures critical context is preserved and accessible.
* **Enhance AI-generated code reviews.** Arc doesn't just comment on code—it provides rich contextual metadata that demonstrates why a change is safe (or isn't).
* **Local-first, privacy-first.** All graph building runs locally; no proprietary code leaves your environment unless you explicitly share it.
* **Built for high-stakes engineering.** Designed for fintech, blockchain, and payment-rail providers where understanding code changes is mission-critical.

**Arc = memory + causal relationships + provenance—your knowledge foundation for the era of autonomous code.**

## Arc Ecosystem

<div align="center">
  <img src="public/arc-vision.png" alt="Arc Memory Ecosystem Diagram" width="1200"/>
</div>

### How It Works

- **Data Sources** (GitHub, Git, Linear, ADRs) feed into the **Arc CLI**, which builds a local-first Temporal Knowledge Graph capturing the why behind your code.

- The **Knowledge Graph** includes causal relationships, semantic analysis, and temporal patterns, providing a rich foundation for understanding your codebase.

- The **Export Functionality** creates optimized JSON payloads for the PR bot, enabling it to provide context-rich insights during code reviews.

- Through the **GitHub PR Bot**, you interact with decision trails directly in your pull request workflow.

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- Python 3.10 or higher
- Git repository with commit history
- GitHub account (for GitHub integration)
- Linear account (optional, for Linear integration)

### Installation

Arc requires Python 3.10 or higher and is compatible with Python 3.10, 3.11, and 3.12.

```bash
pip install arc-memory
```

Or using UV:

```bash
uv pip install arc-memory
```

### Quick Start Workflow

1. **Build your knowledge graph**

   ```bash
   # Build with GitHub data
   arc build --github

   # Build with Linear data
   arc build --linear

   # Build with both GitHub and Linear data
   arc build --github --linear

   # Build with LLM enhancement for deeper analysis
   arc build --github --linear --llm-enhancement standard
   ```

   This will analyze your repository and build a local knowledge graph. You'll see progress indicators and a summary of ingested entities when complete.

2. **Understand the why behind your code**

   ```bash
   arc why file path/to/file.py 42
   ```

   This will show you the decision trail for line 42 in file.py, including related commits, PRs, and issues that explain why this code exists.

3. **Export knowledge graph for PR bot**

   ```bash
   arc export <commit-sha> export.json
   ```

   This will export a relevant slice of the knowledge graph for the PR bot to use, including causal relationships and reasoning paths.

## Core Features

### Knowledge Graph (`arc build`)

Build a comprehensive temporal knowledge graph with causal relationships:

```bash
# Build the full knowledge graph with GitHub and Linear data
arc build --github --linear

# Include LLM enhancement for deeper analysis
arc build --llm-enhancement standard

# Update incrementally
arc build --incremental --github --linear

# Specify a custom repository path
arc build --repo /path/to/repo --github --linear
```

[Learn more about building graphs →](./docs/cli/build.md)

### Decision Trails (`arc why`)

Understand the reasoning behind code:

```bash
# Show decision trail for a specific file and line
arc why file path/to/file.py 42

# Show decision trail for a specific commit
arc why commit abc123

# Ask natural language questions about your codebase
arc why query "Who implemented the authentication feature?"
arc why query "Why was the database schema changed last month?"
arc why query "What decision led to using SQLite instead of PostgreSQL?"
```

[Learn more about decision trails →](./docs/cli/why.md)

### Export for PR Bot (`arc export`)

Export a relevant slice of the knowledge graph for the PR bot:

```bash
# Export for a specific commit
arc export <commit-sha> export.json

# Export with compression
arc export <commit-sha> export.json --compress

# Export with signing
arc export <commit-sha> export.json --sign
```

[Learn more about export →](./docs/cli/export.md)

### Example Scenario: Understanding a Code Change

Let's walk through a complete example of using Arc to understand a code change:

1. After making changes to your API service:
   ```bash
   git add api/routes.py
   git commit -m "Add rate limiting to /users endpoint"
   ```

2. Build your knowledge graph to include this change:
   ```bash
   arc build --github --linear --llm-enhancement standard
   ```

3. Understand why this endpoint was implemented:
   ```bash
   arc why file api/routes.py 42
   ```

   This will show you the decision trail leading to this code, including related issues, PRs, and commits.

   Or, ask a direct question in natural language:
   ```bash
   arc why query "Why was rate limiting added to the users endpoint?"
   ```

4. Export the knowledge graph for PR review:
   ```bash
   arc export HEAD export.json --compress
   ```

   This creates a JSON payload that the PR bot can use to provide context-rich insights during code review.

### The Flywheel Effect

As you use Arc in your daily workflow:

1. Your knowledge graph becomes more valuable with each commit, PR, and issue
2. Causal relationships become more comprehensive as the graph evolves
3. PR reviews become more efficient with rich contextual information
4. Decision trails become richer and more insightful

This creates a reinforcing flywheel where each component makes the others more powerful.

## Telemetry

Arc includes optional, privacy-respecting telemetry to help us improve the product:

- **Anonymous**: No personally identifiable information is collected
- **Opt-in**: Disabled by default, enable with `arc config telemetry on`
- **Transparent**: All collected data is documented and visible
- **Focused**: Only collects command usage and session metrics

Telemetry is disabled by default. To enable it: `arc config telemetry on`
To disable telemetry: `arc config telemetry off`

## Documentation

### CLI Commands

#### Core Workflow
- [Build](./docs/cli/build.md) - Building the knowledge graph (`arc build`)
- [Why](./docs/cli/why.md) - Show decision trail for a file line (`arc why`)
- [Export](./docs/cli/export.md) - Export knowledge graph for PR bot (`arc export`)

#### Additional Commands
- [Relate](./docs/cli/relate.md) - Show related nodes for an entity (`arc relate`)
- [Doctor](./docs/cli/doctor.md) - Checking graph status and diagnostics (`arc doctor`)

### Usage Examples
- [Building Graphs](./docs/examples/building-graphs.md) - Examples of building knowledge graphs
- [Tracing History](./docs/examples/tracing-history.md) - Examples of tracing history
- [Custom Plugins](./docs/examples/custom-plugins.md) - Creating custom data source plugins

For additional documentation, visit [arc.computer](https://www.arc.computer).

## License

MIT
