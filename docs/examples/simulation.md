# Arc Sim Examples

This document provides examples of using the `arc sim` command for different scenarios.

## Basic Usage

The simplest way to use `arc sim` is with no arguments, which analyzes the latest commit:

```bash
arc sim
```

This will:
1. Extract the diff between HEAD~1 and HEAD
2. Identify affected services
3. Generate a simulation manifest
4. Run a network latency fault injection experiment
5. Analyze the results and calculate a risk score
6. Generate an explanation
7. Output the results to stdout

## Analyzing Specific Commits

You can analyze specific commits by providing a rev-range:

```bash
arc sim --rev-range HEAD~3..HEAD
```

This analyzes the last 3 commits.

You can also analyze changes between branches:

```bash
arc sim --rev-range main..feature-branch
```

This analyzes the changes between the main branch and the feature branch.

## Using a Pre-serialized Diff

If you already have a diff in JSON format, you can use it directly:

```bash
arc sim --diff ./my-diff.json
```

The diff file should have the following format:

```json
{
  "files": [
    {
      "path": "file1.py",
      "additions": 10,
      "deletions": 5,
      "status": "modified"
    },
    {
      "path": "file2.py",
      "additions": 20,
      "deletions": 15,
      "status": "modified"
    }
  ],
  "commit_count": 1,
  "range": "HEAD~1..HEAD",
  "start_commit": "abc123",
  "end_commit": "def456",
  "timestamp": "2023-01-01T00:00:00Z"
}
```

## Using Different Fault Scenarios

You can use different fault scenarios:

```bash
arc sim --scenario cpu_stress
```

To see all available scenarios:

```bash
arc sim list-scenarios
```

### Network Latency Scenario

The network latency scenario simulates network latency between services:

```bash
arc sim --scenario network_latency
```

This will introduce latency between the affected services and measure the impact on response times and error rates.

Example output:

```json
{
  "sim_id": "sim_HEAD_1_HEAD",
  "risk_score": 35,
  "services": ["api-service", "database-service"],
  "metrics": {
    "latency_ms": 500,
    "error_rate": 0.05,
    "node_count": 1,
    "pod_count": 5,
    "service_count": 3
  },
  "explanation": "The network_latency simulation with severity 50 was applied to 2 affected services (api-service, database-service). The simulation introduced 500ms of latency and resulted in a 5% error rate. The risk score is 35/100, which is below the threshold of 50.",
  "manifest_hash": "abc123",
  "commit_target": "def456",
  "timestamp": "2023-01-01T00:00:00Z",
  "diff_hash": "ghi789"
}
```

### CPU Stress Scenario

The CPU stress scenario simulates CPU stress on services:

```bash
arc sim --scenario cpu_stress
```

This will introduce CPU stress on the affected services and measure the impact on response times, error rates, and resource usage.

Example output:

```json
{
  "sim_id": "sim_HEAD_1_HEAD",
  "risk_score": 45,
  "services": ["api-service", "database-service"],
  "metrics": {
    "latency_ms": 750,
    "error_rate": 0.08,
    "node_count": 1,
    "pod_count": 5,
    "service_count": 3,
    "cpu_usage": {
      "api-service": 0.85,
      "database-service": 0.92
    }
  },
  "explanation": "The cpu_stress simulation with severity 50 was applied to 2 affected services (api-service, database-service). The simulation introduced CPU stress and resulted in 750ms of latency and an 8% error rate. CPU usage peaked at 92% for database-service. The risk score is 45/100, which is below the threshold of 50.",
  "manifest_hash": "abc123",
  "commit_target": "def456",
  "timestamp": "2023-01-01T00:00:00Z",
  "diff_hash": "ghi789"
}
```

### Memory Stress Scenario

The memory stress scenario simulates memory pressure on services:

```bash
arc sim --scenario memory_stress
```

This will introduce memory pressure on the affected services and measure the impact on response times, error rates, and resource usage.

Example output:

```json
{
  "sim_id": "sim_HEAD_1_HEAD",
  "risk_score": 55,
  "services": ["api-service", "database-service"],
  "metrics": {
    "latency_ms": 850,
    "error_rate": 0.12,
    "node_count": 1,
    "pod_count": 5,
    "service_count": 3,
    "memory_usage": {
      "api-service": 750,
      "database-service": 950
    }
  },
  "explanation": "The memory_stress simulation with severity 50 was applied to 2 affected services (api-service, database-service). The simulation introduced memory pressure and resulted in 850ms of latency and a 12% error rate. Memory usage peaked at 950MB for database-service. The risk score is 55/100, which exceeds the threshold of 50.",
  "manifest_hash": "abc123",
  "commit_target": "def456",
  "timestamp": "2023-01-01T00:00:00Z",
  "diff_hash": "ghi789"
}
```

## Setting a Custom Severity Threshold

You can set a custom severity threshold:

```bash
arc sim --severity 75
```

This will fail (exit code 1) if the risk score is 75 or higher.

## Setting a Custom Timeout

You can set a custom timeout:

```bash
arc sim --timeout 300
```

This will limit the simulation to 5 minutes.

## Saving Results to a File

You can save the results to a file:

```bash
arc sim --output ./simulation-results.json
```

## Enabling Verbose Output

You can enable verbose output:

```bash
arc sim --verbose
```

This will provide more detailed output during the simulation process.

## Opening the UI

If you have VS Code installed, you can open the simulation results in a webview:

```bash
arc sim --open-ui
```

## Combining Options

You can combine multiple options:

```bash
arc sim --rev-range HEAD~3..HEAD --scenario cpu_stress --severity 75 --timeout 300 --output ./simulation-results.json --verbose
```

## Real-World Example: API Service Changes

Let's say you've made changes to an API service that might affect performance. You can simulate the impact of these changes:

```bash
arc sim --rev-range main..feature-api-changes --scenario network_latency
```

This will simulate network latency between the API service and its dependencies, helping you understand the potential impact of your changes.

## Real-World Example: Database Schema Changes

Let's say you've made changes to a database schema that might affect query performance. You can simulate the impact of these changes:

```bash
arc sim --rev-range main..feature-db-schema --scenario cpu_stress
```

This will simulate CPU stress on the database service, helping you understand the potential impact of your schema changes on query performance.

## Troubleshooting

### Missing API Keys

If you see an error about missing API keys, make sure you have set the required environment variables:

```bash
export E2B_API_KEY=your_e2b_api_key
export OPENAI_API_KEY=your_openai_api_key
```

Or create a `.env` file in your repository root with these variables.

### Simulation Failures

If the simulation fails, check the following:
- Make sure you have the required dependencies installed
- Check that your API keys are valid
- Try increasing the timeout if the simulation is taking too long
- Try using a different scenario if the current one is not working

### Invalid Diff Format

If you see an error about an invalid diff format, make sure your diff file has the correct structure:

```json
{
  "files": [
    {
      "path": "file1.py",
      "additions": 10,
      "deletions": 5,
      "status": "modified"
    }
  ],
  "commit_count": 1,
  "range": "HEAD~1..HEAD",
  "start_commit": "abc123",
  "end_commit": "def456",
  "timestamp": "2023-01-01T00:00:00Z"
}
```

### No Affected Services

If the simulation doesn't find any affected services, it might be because:
- The diff doesn't contain any changes to files that map to services
- The causal graph doesn't have any information about the changed files

Try using the `--verbose` flag to see more information about the diff analysis.

### High Risk Scores

If you're consistently getting high risk scores, consider:
- Reducing the scope of your changes
- Breaking your changes into smaller, more focused changes
- Adding more tests to ensure your changes don't introduce regressions
- Improving the resilience of your services to handle failures better

## Advanced Usage

### Custom Diff Files

You can create custom diff files to simulate specific changes:

```json
{
  "files": [
    {
      "path": "api/routes.py",
      "additions": 10,
      "deletions": 5,
      "status": "modified"
    },
    {
      "path": "database/models.py",
      "additions": 20,
      "deletions": 15,
      "status": "modified"
    }
  ],
  "commit_count": 1,
  "range": "custom",
  "start_commit": "custom",
  "end_commit": "custom",
  "timestamp": "2023-01-01T00:00:00Z"
}
```

Then run the simulation with:

```bash
arc sim --diff ./custom-diff.json
```

### GitHub Integration

You can use `arc sim` with GitHub PRs by creating a diff file with the PR information:

```json
{
  "owner": "your-org",
  "repo": "your-repo",
  "pr_number": 123
}
```

Then run the simulation with:

```bash
arc sim --diff ./github-pr.json
```

This will fetch the diff from the GitHub PR and run the simulation.

### CI/CD Integration

You can integrate `arc sim` into your CI/CD pipeline to automatically run simulations on pull requests. See the [CLI documentation](../cli/sim.md#integration-with-cicd) for an example GitHub Actions workflow.
