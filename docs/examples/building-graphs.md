# Building Knowledge Graphs

This guide provides examples of how to build knowledge graphs with Arc Memory for different scenarios.

**Related Documentation:**
- [Authentication Commands](../cli/auth.md) - Authenticate with GitHub
- [Build Commands](../cli/build.md) - Reference for build commands
- [Doctor Commands](../cli/doctor.md) - Verify your build status
- [Build API](../api/build.md) - Programmatic access to build functionality

## Basic Graph Building

The simplest way to build a knowledge graph is to run the `arc build` command in your repository:

```bash
# Navigate to your repository
cd /path/to/your/repo

# Build the knowledge graph
arc build
```

This will:
1. Scan your Git repository for commits
2. Fetch GitHub PRs and issues (if authenticated)
3. Find ADRs in your repository
4. Build a knowledge graph in `~/.arc/graph.db`

## Incremental Builds

For faster updates after the initial build, use incremental builds:

```bash
# Build incrementally (only process new data)
arc build --incremental
```

Incremental builds are much faster because they only process data that has changed since the last build. This is especially useful for large repositories or daily updates.

## Limiting the Build Scope

For large repositories, you may want to limit the scope of the build:

```bash
# Limit to the last 100 commits
arc build --max-commits 100

# Limit to commits from the last 30 days
arc build --days 30

# Combine limits
arc build --max-commits 100 --days 30
```

## Custom Output Location

By default, Arc Memory stores the knowledge graph in `~/.arc/graph.db`. You can specify a custom location:

```bash
# Build with a custom output path
arc build --output /path/to/output.db
```

This is useful for:
- Storing graphs for different projects separately
- Sharing graphs with team members
- Backing up graphs

## Building with GitHub Authentication

To include GitHub PRs and issues in your graph, authenticate with GitHub first:

```bash
# Authenticate with GitHub
arc auth gh

# Then build the graph
arc build
```

You can also provide a token directly:

```bash
# Build with a specific GitHub token
arc build --token ghp_1234567890abcdef
```

## Building for a Specific Repository

By default, Arc Memory builds the graph for the current directory. You can specify a different repository:

```bash
# Build for a specific repository
arc build --repo /path/to/repo
```

## CI/CD Integration

For team-wide graph updates, you can integrate Arc Memory into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
name: Update Knowledge Graph

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0  # Fetch all history

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install arc-memory

    - name: Build knowledge graph
      run: |
        arc build --token ${{ secrets.GITHUB_TOKEN }}

    - name: Upload graph
      uses: actions/upload-artifact@v3
      with:
        name: knowledge-graph
        path: ~/.arc/graph.db.zst
```

## Monitoring Build Progress

The build process shows progress for each plugin:

```
⠋ Ingesting git data...
⠙ Ingesting github data...
⠹ Ingesting adr data...
```

For more detailed logs, use the `--debug` flag:

```bash
arc build --debug
```

## Verifying the Build

After building, you can verify the graph with the doctor command:

```bash
arc doctor
```

This will show statistics about your knowledge graph, including the number of nodes and edges.

## Troubleshooting Common Issues

### GitHub Rate Limiting

If you hit GitHub API rate limits:

```bash
# Authenticate with GitHub to get higher rate limits
arc auth gh

# Then build again
arc build
```

### Large Repositories

For very large repositories:

```bash
# Use incremental builds after the initial build
arc build --incremental

# Or limit the scope
arc build --max-commits 1000 --days 90
```

### Missing Data

If data is missing from your graph:

1. Ensure you're authenticated with GitHub: `arc auth gh`
2. Check that your repository has the expected structure
3. Run a full build: `arc build` (without `--incremental`)
4. Verify with `arc doctor`
