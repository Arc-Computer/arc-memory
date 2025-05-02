# `arc sim` Command

The `arc sim` command enables simulation-based impact prediction by analyzing code diffs, running targeted fault injection experiments in isolated sandbox environments, and providing risk assessments with attestation.

## Overview

Arc Sim helps you understand the potential impact of your code changes before they are merged, significantly reducing the risk of production incidents. It works by:

1. Analyzing the diff between commits to identify affected services
2. Building a causal graph to understand service dependencies
3. Generating a simulation manifest for fault injection
4. Running the simulation in an isolated sandbox environment
5. Collecting metrics and calculating a risk score
6. Generating an explanation and attestation

## Usage

```bash
arc sim [OPTIONS]
```

## Required (one of)

- `--rev-range TEXT` - Git rev-range to analyze (default: HEAD~1..HEAD)
- `--diff PATH` - Path to pre-serialized diff JSON

## Options

- `--scenario TEXT` - Fault scenario ID (default: network_latency)
- `--severity INT` - CI fail threshold 0-100 (default: 50)
- `--timeout INT` - Max runtime in seconds (default: 600)
- `--output PATH` - Write result JSON to file (default: stdout)
- `--memory / --no-memory` - Enable memory integration to learn from past simulations (default: no-memory)
- `--open-ui / --no-ui` - Open VS Code webview if available (default: no-ui)
- `-v, --verbose` - Enable verbose output
- `--debug` - Enable debug logging

## Subcommands

### `list-scenarios`

List available fault scenarios.

```bash
arc sim list-scenarios
```

### `history`

View past simulation results.

```bash
arc sim history [OPTIONS]
```

#### Options

- `--service TEXT` - Filter by service
- `--file TEXT` - Filter by file
- `--limit INT` - Maximum number of results (default: 10)
- `--output PATH` - Write result JSON to file

#### Examples

```bash
# View all recent simulations
arc sim history

# View simulations for a specific service
arc sim history --service api-service

# View simulations for a specific file
arc sim history --file src/api.py

# Limit the number of results
arc sim history --limit 5

# Save results to a file
arc sim history --output ./simulation-history.json
```

## Exit Codes

- `0`: Success - Simulation completed successfully with risk score below severity threshold
- `1`: Failure - Simulation completed but risk score exceeds severity threshold
- `2`: Error - Simulation failed to complete due to technical issues
- `3`: Invalid Input - Command arguments are invalid or missing

## Examples

### Basic Usage

```bash
arc sim
```

This will analyze the diff between HEAD~1 and HEAD, run a network latency simulation, and output the results to stdout.

### Analyze Specific Commits

```bash
arc sim --rev-range HEAD~3..HEAD
```

This will analyze the diff between HEAD~3 and HEAD, allowing you to simulate the impact of multiple commits.

### Use a Different Scenario

```bash
arc sim --scenario cpu_stress --severity 75
```

This will run a CPU stress simulation with a severity threshold of 75.

### Save Results to a File

```bash
arc sim --output ./simulation-results.json
```

This will save the simulation results to a file instead of printing them to stdout.

### Enable Memory Integration

```bash
arc sim --memory
```

This will enable memory integration, allowing the simulation to learn from past simulations and provide more accurate predictions.

### Enable Verbose Output

```bash
arc sim --verbose
```

This will provide more detailed output during the simulation process.

## Output Format

The command outputs a JSON object with the following structure:

```json
{
  "sim_id": "string",
  "risk_score": 0-100,
  "services": ["service1", "service2"],
  "metrics": {
    "latency_ms": 250,
    "error_rate": 0.05,
    "node_count": 1,
    "pod_count": 5,
    "service_count": 3,
    "cpu_usage": {
      "service1": 0.5,
      "service2": 0.7
    },
    "memory_usage": {
      "service1": 200,
      "service2": 300
    }
  },
  "explanation": "string",
  "manifest_hash": "string",
  "commit_target": "string",
  "timestamp": "ISO-8601 timestamp",
  "diff_hash": "string",
  "memory": {
    "memory_used": true,
    "similar_simulations_count": 2,
    "simulation_stored": true
  }
}
```

### Output Fields

- `sim_id`: A unique identifier for the simulation
- `risk_score`: A score from 0-100 indicating the risk level of the changes
- `services`: A list of affected services
- `metrics`: A dictionary of metrics collected during the simulation
- `explanation`: A human-readable explanation of the simulation results
- `manifest_hash`: A hash of the simulation manifest
- `commit_target`: The target commit SHA
- `timestamp`: The time the simulation was run
- `diff_hash`: A hash of the diff that was analyzed
- `memory`: Memory integration information (only present if `--memory` flag is used)
  - `memory_used`: Whether memory integration was used
  - `similar_simulations_count`: Number of similar simulations found
  - `simulation_stored`: Whether the simulation was stored in memory

## Environment Variables

The following environment variables are used by the `arc sim` command:

- `E2B_API_KEY` - API key for E2B sandbox environments
- `OPENAI_API_KEY` - API key for OpenAI (used for explanation generation)
- `ANTHROPIC_API_KEY` - API key for Anthropic (alternative to OpenAI)
- `ARC_SIGNING_KEY` - Key used for signing attestations (optional)

You can set these in a `.env` file in your repository root.

## How It Works

### 1. Diff Analysis

The command first analyzes the diff between the specified commits to identify which files have changed. It then maps these files to services based on file paths and extensions.

### 2. Causal Graph

A causal graph is built to understand the dependencies between services. This helps identify which services might be affected by changes to other services.

### 3. Simulation Manifest

A simulation manifest is generated based on the affected services and the selected scenario. This manifest defines the fault injection experiment that will be run.

### 4. Sandbox Environment

The simulation is run in an isolated sandbox environment using E2B. This ensures that the simulation doesn't affect your local environment or production systems.

### 5. Fault Injection

Faults are injected into the sandbox environment using Chaos Mesh. This simulates real-world failure scenarios like network latency, CPU stress, or memory pressure.

### 6. Metrics Collection

Metrics are collected during the simulation to measure the impact of the faults on the affected services.

### 7. Risk Assessment

A risk score is calculated based on the collected metrics, the severity of the faults, and the number of affected services.

### 8. Explanation and Attestation

An explanation is generated to help you understand the simulation results. An attestation is also generated to provide a cryptographically verifiable record of the simulation.

### 9. Memory Integration (Optional)

When the `--memory` flag is enabled, the simulation results are stored in the knowledge graph, creating a reinforcing flywheel where simulation results feed back into the knowledge graph, making future simulations more accurate and providing richer context for decision-making.

The memory integration provides several benefits:

1. **Historical Context**: The system retrieves relevant past simulations to enhance the explanation with historical context. This includes comparing the current risk score with historical averages and providing examples of similar simulations.

2. **Risk Assessment Calibration**: The risk score is calibrated based on historical data, providing a more accurate assessment of the potential impact of the changes.

3. **Pattern Recognition**: Arc Memory can recognize patterns in code changes that have led to specific types of failures in the past, helping you avoid similar issues in the future.

4. **Service Impact History**: The system tracks how specific services respond to different types of changes, allowing it to provide more accurate predictions for those services.

The enhanced explanation includes a "Historical Context" section that shows:
- How the current risk score compares to similar changes in the past
- A list of relevant historical simulations with their risk scores and brief summaries
- Patterns or trends identified across simulations

## Integration with CI/CD

You can integrate `arc sim` into your CI/CD pipeline to automatically run simulations on pull requests. For example, in GitHub Actions:

```yaml
name: Arc Sim

on:
  pull_request:
    branches: [ main ]

jobs:
  simulate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install arc-memory
      - name: Run simulation
        run: |
          arc sim --rev-range ${{ github.event.pull_request.base.sha }}..${{ github.event.pull_request.head.sha }} --severity 75 --output sim-results.json
        env:
          E2B_API_KEY: ${{ secrets.E2B_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      - name: Upload simulation results
        uses: actions/upload-artifact@v3
        with:
          name: sim-results
          path: sim-results.json
```

This will run a simulation on every pull request and upload the results as an artifact.
