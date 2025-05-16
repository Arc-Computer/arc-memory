# Cross-Repository Explorer

This example demonstrates Arc Memory's powerful multi-repository capabilities, allowing you to analyze relationships and dependencies across repository boundaries.

## Overview

The Cross-Repository Explorer showcases how Arc Memory can:

1. **Build a unified knowledge graph** across multiple repositories
2. **Discover cross-repository dependencies** between components
3. **Trace decisions** that span repository boundaries
4. **Query across repositories** to understand system-wide patterns

This capability is particularly valuable for:
- Microservice architectures
- Monorepos with multiple components
- Systems with frontend/backend separation
- Any scenario where code is split across multiple repositories

## Prerequisites

- Arc Memory installed: `pip install arc-memory[all]`
- Access to multiple repositories you want to analyze

## Usage

```bash
# Run the example with your repositories
python cross_repo_explorer.py --repos /path/to/repo1 /path/to/repo2 /path/to/repo3

# Or specify repository names
python cross_repo_explorer.py --repos /path/to/repo1 /path/to/repo2 --names "Frontend" "Backend"

# Run a specific analysis
python cross_repo_explorer.py --repos /path/to/repo1 /path/to/repo2 --analysis dependencies
```

Available analysis types:
- `dependencies`: Analyze cross-repository dependencies
- `decisions`: Trace decisions that span repositories
- `components`: Identify shared components across repositories
- `all`: Run all analyses (default)

## Example Output

```
=== Cross-Repository Dependencies ===

Frontend → Backend:
- frontend/src/api/client.js → backend/src/controllers/api.js
  - HTTP API calls to endpoints
  - 8 dependencies found

Backend → Database:
- backend/src/models/user.js → database/schemas/user.sql
  - Schema dependencies
  - 5 dependencies found

=== Cross-Repository Decisions ===

Decision: "Implement OAuth authentication"
- Affected repositories: Frontend, Backend, Auth Service
- Related PRs:
  - Frontend #42: "Add OAuth UI components"
  - Backend #78: "Implement OAuth endpoints"
  - Auth Service #15: "Create OAuth provider integration"

=== Shared Components ===

Component: "User Authentication"
- Frontend: frontend/src/components/auth/*
- Backend: backend/src/services/auth/*
- Auth Service: auth/src/*
```

## How It Works

The Cross-Repository Explorer uses Arc Memory's SDK to:

1. **Add repositories** to the knowledge graph using `arc.add_repository()`
2. **Build knowledge graphs** for each repository using `arc.build_repository()`
3. **Set active repositories** for queries using `arc.set_active_repositories()`
4. **Query across repositories** using repository-aware methods

It then analyzes the results to identify cross-repository relationships and presents them in an easy-to-understand format.

## Implementation Details

The example consists of:

- `cross_repo_explorer.py`: Main script that orchestrates the analysis
- `analyzers/`: Directory containing different analysis modules:
  - `dependency_analyzer.py`: Analyzes cross-repository dependencies
  - `decision_analyzer.py`: Traces decisions across repositories
  - `component_analyzer.py`: Identifies shared components

Each analyzer uses Arc Memory's SDK to query the knowledge graph and extract relevant information.

## Key Concepts

### Repository Identity

Each repository is assigned a unique ID based on its path. This ID is used to tag all nodes from that repository in the knowledge graph.

### Unified Knowledge Graph

All repositories share a single knowledge graph database, with nodes tagged by their source repository. This enables cross-repository queries and analysis.

### Repository Context

Every node maintains its repository context, allowing for repository-aware filtering and visualization.

### Cross-Repository Relationships

Edges can connect nodes from different repositories, enabling analysis of dependencies and relationships that span repository boundaries.

## Customization

You can customize the Cross-Repository Explorer by:

1. **Adding new analyzers**: Create new modules in the `analyzers/` directory
2. **Modifying existing analyzers**: Adjust the analysis logic to focus on specific aspects
3. **Changing the visualization**: Update the output formatting to suit your needs

## Next Steps

After exploring this example, you might want to:

1. **Integrate cross-repository analysis** into your CI/CD pipeline
2. **Build custom visualizations** of cross-repository dependencies
3. **Create automated reports** of cross-repository impacts for PRs
4. **Develop architecture validation tools** that enforce cross-repository boundaries
