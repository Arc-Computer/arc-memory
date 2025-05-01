# Arc: The What-If Engine for Software

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

*Arc is the local-first "what-if" engine for software: it captures the **why** behind every line of code, then simulates how new changes will ripple through your system **before** you hit Merge.*

## What Arc Actually Does

1. **Record the why.**
   Arc's Temporal Knowledge Graph ingests commits, PRs, issues, and ADRs to preserve architectural intent and decision history—entirely on your machine.

2. **Model the system.**
   From that history Arc derives a **causal graph** of services, data flows, and constraints—a lightweight world-model that stays in sync with the codebase.

3. **Predict the blast-radius.**
   A one-line CLI (`arc sim`) spins up an isolated sandbox, injects targeted chaos (network latency, CPU stress, etc.), and returns a risk score plus human-readable explanation for the current diff.

4. **Prove it.**
   Every simulation writes a signed attestation that links input code, fault manifest, and metrics—auditable evidence that the change was tested under realistic failure modes.

## Why It Matters

* **Catch outages before they exist.** Shift chaos left from staging to the developer's laptop; trim MTTR and stop bad PRs at the gate.
* **Trust AI suggestions.** Arc doesn't just comment on code—it *proves* why a suggestion is safe (or isn't) with sandbox data and a verifiable chain of custody.
* **Local-first, privacy-first.** All graphs and simulations run inside a disposable E2B sandbox; no proprietary code leaves your environment.
* **Built to extend.** The same graph and attestation layer will power live-telemetry world-models and multi-agent change control as teams grow.

**Arc = memory + simulation + proof—your safety net for the era of autonomous code.**

## Arc Ecosystem

<div align="center">
  <img src="public/arc-vision-diagram.png" alt="Arc Memory Ecosystem Diagram" width="1200"/>
</div>

### How It Works

- **Data Sources** (GitHub, Git, ADRs) feed into the **Arc CLI**, which builds a local-first Temporal Knowledge Graph capturing the why behind your code.

- The **Simulation Engine** uses this graph to predict the impact of changes, running fault injection experiments in isolated sandboxes.

- The **Arc MCP Server** provides your knowledge graph to AI assistants, enabling them to understand your codebase's history and architecture.

- Through the **VS Code Extension**, you interact with decision trails and simulation results directly in your development environment.

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- Python 3.10 or higher
- Git repository with commit history
- E2B API key (for simulation features)
- OpenAI API key (for explanation generation)

Note: GitHub authentication is built into the CLI with the `arc auth gh` command. You don't need to provide your own GitHub token unless you're contributing to this project.

### Environment Setup

Arc uses the following environment variables:

```bash
# Create a .env file in your repository root
E2B_API_KEY=your_e2b_api_key           # Required for simulations
OPENAI_API_KEY=your_openai_api_key     # Required for explanations
```

You can obtain these keys from:
- E2B API key: [e2b.dev](https://e2b.dev)
- OpenAI API key: [platform.openai.com](https://platform.openai.com)

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

1. **Authenticate with GitHub**

   ```bash
   arc auth gh
   ```

   This will guide you through authenticating with GitHub. You'll see a success message when complete.

2. **Build your knowledge graph**

   ```bash
   arc build
   ```

   This will analyze your repository and build a local knowledge graph. You'll see progress indicators and a summary of ingested entities when complete.

3. **Understand the why behind your code**

   ```bash
   arc why file path/to/file.py 42
   ```

   This will show you the decision trail for line 42 in file.py, including related commits, PRs, and issues that explain why this code exists.

4. **Simulate the impact of your changes**

   ```bash
   arc sim
   ```

   This will analyze your latest commit, run a simulation in an isolated sandbox, and output a risk assessment with metrics and explanation.

5. **Serve your knowledge graph to LLMs**

   ```bash
   arc serve start
   ```

   This will start the MCP server, allowing AI assistants to access your knowledge graph. You'll see a URL that you can use to connect your LLM.

## Core Features

### Simulation (`arc sim`)

Predict the impact of code changes before merging:

```bash
# Run a simulation on your latest commit
arc sim

# Analyze specific commits
arc sim --rev-range HEAD~3..HEAD

# Use a different fault scenario
arc sim --scenario cpu_stress --severity 75
```

[Learn more about simulation →](./docs/cli/sim.md)

### Decision Trails (`arc why`)

Understand the reasoning behind code:

```bash
# Show decision trail for a specific file and line
arc why file path/to/file.py 42

# Show decision trail for a specific commit
arc why commit abc123
```

[Learn more about decision trails →](./docs/cli/why.md)

### Knowledge Graph (`arc build`)

Build a comprehensive temporal knowledge graph:

```bash
# Build the full knowledge graph
arc build

# Update incrementally
arc build --incremental
```

[Learn more about building graphs →](./docs/cli/build.md)

### LLM Integration (`arc serve`)

Connect your knowledge graph to AI assistants:

```bash
# Start the MCP server
arc serve start
```

[Learn more about LLM integration →](./docs/cli/serve.md)

### Example Scenario: Assessing a Code Change

Let's walk through a complete example of using Arc to assess a code change:

1. After making changes to your API service:
   ```bash
   git add api/routes.py
   git commit -m "Add rate limiting to /users endpoint"
   ```

2. Run a simulation to assess the impact:
   ```bash
   arc sim
   ```

   Output:
   ```json
   {
     "sim_id": "sim_HEAD_1_HEAD",
     "risk_score": 35,
     "services": ["api-service", "auth-service"],
     "metrics": { "latency_ms": 250, "error_rate": 0.02 },
     "explanation": "The rate limiting changes add minimal overhead...",
     "manifest_hash": "abc123",
     "commit_target": "def456",
     "timestamp": "2023-01-01T00:00:00Z"
   }
   ```

3. Understand why this endpoint was implemented:
   ```bash
   arc why file api/routes.py 42
   ```

   This will show you the decision trail leading to this code, including related issues, PRs, and commits.

4. If you want to share this context with AI assistants:
   ```bash
   arc serve start
   ```

   Now your AI assistant can access the knowledge graph and provide context-aware suggestions.

### The Flywheel Effect

As you use Arc in your daily workflow:

1. Your knowledge graph becomes more valuable with each commit, PR, and issue
2. Simulations become more accurate as the causal graph evolves
3. AI assistants gain deeper context about your codebase
4. Decision trails become richer and more insightful

This creates a reinforcing flywheel where each component makes the others more powerful.

## Troubleshooting

Here are solutions to common issues you might encounter:

- **GitHub Authentication Issues**: If you encounter GitHub authentication problems, try running `arc auth gh` again to refresh your authentication.

- **Empty Knowledge Graph**: If `arc build` completes but doesn't find any entities, check that your repository has commit history and that you're in the correct directory.

- **Simulation Errors**: If simulations fail, ensure you have set the required API keys in your environment or .env file.

- **Performance Issues**: For large repositories, try using `arc build --incremental` for faster updates.

- **Missing Dependencies**: If you see import errors, ensure you've installed Arc with all required dependencies: `pip install arc-memory[all]`.

For more help, run `arc doctor` to diagnose common issues or check the [documentation](https://docs.arc.computer).

## Telemetry

Arc includes optional, privacy-respecting telemetry to help us improve the product:

- **Anonymous**: No personally identifiable information is collected
- **Opt-in**: Disabled by default, enable with `arc config telemetry on`
- **Transparent**: All collected data is documented and visible
- **Focused**: Only collects command usage and session metrics for MTTR measurement

Telemetry is disabled by default. To enable it: `arc config telemetry on`
To disable telemetry: `arc config telemetry off`

## Documentation

### CLI Commands

#### Core Workflow
- [Simulation](./docs/cli/sim.md) - Predict the impact of changes (`arc sim`)
- [Why](./docs/cli/why.md) - Show decision trail for a file line (`arc why`)
- [Build](./docs/cli/build.md) - Building the knowledge graph (`arc build`)
- [Serve](./docs/cli/serve.md) - Serve the knowledge graph via MCP (`arc serve`)

#### Additional Commands
- [Authentication](./docs/cli/auth.md) - GitHub authentication commands (`arc auth`)
- [Doctor](./docs/cli/doctor.md) - Checking graph status and diagnostics (`arc doctor`)
- [Relate](./docs/cli/relate.md) - Show related nodes for an entity (`arc relate`)

### Usage Examples
- [Simulation Examples](./docs/examples/simulation.md) - Examples of running simulations
- [Building Graphs](./docs/examples/building-graphs.md) - Examples of building knowledge graphs
- [Tracing History](./docs/examples/tracing-history.md) - Examples of tracing history
- [Custom Plugins](./docs/examples/custom-plugins.md) - Creating custom data source plugins

### API Documentation
- [Build API](./docs/api/build.md) - Build process API
- [Trace API](./docs/api/trace.md) - Trace history API
- [Models](./docs/api/models.md) - Data models
- [Plugins](./docs/api/plugins.md) - Plugin architecture API

For additional documentation, visit [arc.computer](https://www.arc.computer).

## Architecture

Arc consists of three main components:

1. **arc-memory** (this CLI) - Command-line interface and underlying SDK for graph building, simulation, and querying
   - **Temporal Knowledge Graph** - Captures the why behind code
   - **Simulation Engine** - Predicts the impact of changes
   - **Attestation System** - Provides verifiable proof of simulations
   - **Local SQLite Database** - Stores the knowledge graph with direct access for CLI commands
   - **Plugin Architecture** - Extensible system for adding new data sources

2. **arc-mcp-server** - MCP server exposing the knowledge graph to AI assistants
   - Available at [github.com/Arc-Computer/arc-mcp-server](https://github.com/Arc-Computer/arc-mcp-server)
   - Implements Anthropic's Model Context Protocol (MCP) for standardized AI tool access
   - Can be started directly from the CLI with `arc serve start`

3. **vscode-arc-hover** - VS Code extension for displaying decision trails (in development)
   - Will integrate with the MCP server to display trace history
   - Will provide hover cards with decision trails

See our [Architecture Decision Records](./docs/adr/) for more details on design decisions.

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/arc-computer/arc-memory.git
cd arc-memory

# Create a virtual environment with UV
uv venv

# Activate the environment
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows

# Install dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run unit tests
python -m pytest

# Run integration tests
python -m pytest tests/integration

# Run simulation tests
python -m pytest tests/unit/simulate
```

For more development information, see our [contributing guide](./CONTRIBUTING.md).

## License

MIT