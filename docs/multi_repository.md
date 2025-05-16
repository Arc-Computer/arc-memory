# Multi-Repository Support

This document provides a comprehensive reference for Arc Memory's multi-repository support.

## Overview

Arc Memory can analyze and query across multiple repositories within a single knowledge graph. This is particularly useful for:

- Microservice architectures
- Monorepos with multiple components
- Any scenario where understanding cross-repository dependencies is important

## Repository Management

### Adding Repositories

```python
# Using the SDK
from arc_memory.sdk import Arc
arc = Arc(repo_path="/path/to/first/repo")
repo2_id = arc.add_repository("/path/to/second/repo", name="Second Repository")

# Using the CLI
arc repo add /path/to/second/repo --name "Second Repository"
```

### Listing Repositories

```python
# Using the SDK
repos = arc.list_repositories()
for repo in repos:
    print(f"{repo['name']} ({repo['id']})")

# Using the CLI
arc repo list
```

### Building Repositories

```python
# Using the SDK
arc.build_repository(repo_id, include_github=True, include_linear=False)

# Using the CLI
arc repo build repository:1234abcd --github --linear
```

### Setting Active Repositories

```python
# Using the SDK
arc.set_active_repositories([repo1_id, repo2_id])

# Using the CLI
arc repo active repository:1234abcd repository:5678efgh
```

### Updating Repositories

You can update repository information using the SDK or CLI:

```python
# Using the SDK
# Update repository path (generates a new ID)
new_repo_id = arc.update_repository(repo_id, new_path="/new/path/to/repo")

# Update repository name
arc.update_repository(repo_id, new_name="New Repository Name")

# Update multiple properties
arc.update_repository(
    repo_id,
    new_name="New Name",
    new_url="https://github.com/new/url",
    new_default_branch="develop"
)
```

```bash
# Using the CLI
# Update repository path
arc repo update repository:1234abcd --path /new/path/to/repo

# Update repository name
arc repo update repository:1234abcd --name "New Repository Name"

# Update multiple properties
arc repo update repository:1234abcd --name "New Name" --url "https://github.com/new/url" --default-branch develop
```

When updating a repository path:
- A new repository ID will be generated based on the new path
- All nodes will be updated to use the new repository ID
- The old repository record will be removed
- Active repositories will be updated to use the new ID

### Removing Repositories

You can remove repositories from the knowledge graph using the SDK or CLI:

```python
# Using the SDK
# Option 1: Remove repository but keep its nodes
arc.remove_repository(repo_id)

# Option 2: Remove repository and delete all its nodes
arc.remove_repository(repo_id, delete_nodes=True)
```

```bash
# Using the CLI
# Option 1: Remove repository but keep its nodes
arc repo remove repository:1234abcd

# Option 2: Remove repository and delete all its nodes
arc repo remove repository:1234abcd --delete-nodes

# Option 3: Remove without confirmation
arc repo remove repository:1234abcd --force
```

When removing a repository:
- You can choose to delete all nodes from that repository or keep them
- If you keep the nodes, they will no longer be associated with any repository
- Cross-repository edges will be preserved unless you delete the nodes

## Querying Across Repositories

### Basic Queries

```python
# Using the SDK
# Method 1: Use active repositories
arc.set_active_repositories([repo1_id, repo2_id])
result = arc.query("How do the authentication components interact?")

# Method 2: Specify repositories for a specific query
result = arc.query(
    "How do the authentication components interact?",
    repo_ids=[repo1_id, repo2_id]
)

# Using the CLI
arc repo active repository:1234abcd repository:5678efgh
arc why query "How do the authentication components interact?"
```

### Advanced Queries

```python
# Get related entities across repositories
related = arc.get_related_entities(
    "component:auth-service",
    repo_ids=[repo1_id, repo2_id]
)

# Analyze impact across repositories
impact = arc.analyze_component_impact(
    "file:src/auth/login.py",
    repo_ids=[repo1_id, repo2_id]
)
```

## Technical Implementation

### Repository Identification

Repositories are identified by a unique ID: `repository:{md5_hash_of_absolute_path}`

This ensures deterministic IDs even if repositories are moved.

### Node Tagging

Every node in the knowledge graph has a `repo_id` field that links it to its source repository.

### Database Schema

The multi-repository support is implemented with these key database tables:

```sql
-- Repositories table
CREATE TABLE repositories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT,
    local_path TEXT NOT NULL,
    default_branch TEXT DEFAULT 'main',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
)

-- Nodes table with repository ID
CREATE TABLE nodes(
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT,
    body TEXT,
    timestamp TEXT,
    repo_id TEXT,  -- Links node to specific repository
    extra TEXT
)

-- Index on repository ID for efficient filtering
CREATE INDEX idx_nodes_repo_id ON nodes(repo_id)
```

### Cross-Repository Relationships

Edges can connect nodes from different repositories, enabling analysis of cross-repository dependencies.

## Data Flow

1. **Repository Registration**
   - Each repository is registered with a unique ID
   - Repository metadata is stored in the `repositories` table

2. **Node Creation**
   - When nodes are created, they are tagged with their source repository's ID
   - The `repo_id` field links each node to its source repository

3. **Query Filtering**
   - Queries can be filtered by repository ID
   - If no repository IDs are specified, active repositories are used

4. **Cross-Repository Analysis**
   - Relationships between nodes from different repositories are preserved
   - This enables analysis of dependencies across repository boundaries

## Best Practices

1. **Build repositories individually** for better performance and control
2. **Use descriptive repository names** to easily identify them in queries and results
3. **Set active repositories** before running queries to ensure consistent results
4. **Use repository IDs explicitly** in programmatic queries for clarity
5. **Consider repository boundaries** when analyzing relationships and dependencies

## Common Use Cases

### Microservice Architecture Analysis

```python
# Analyze dependencies between microservices
result = arc.query(
    "How does the auth service interact with the user service?",
    repo_ids=[auth_service_repo_id, user_service_repo_id]
)
```

### Cross-Repository Impact Analysis

```python
# Analyze the impact of changes in one repository on another
impact = arc.analyze_component_impact(
    "file:auth-service/src/auth.py",
    repo_ids=[auth_service_repo_id, api_gateway_repo_id]
)
```

### Architecture Visualization

```python
# Get all system components across repositories
components = arc.get_nodes_by_type(
    NodeType.COMPONENT,
    repo_ids=[repo1_id, repo2_id, repo3_id]
)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **"Repository with ID X does not exist"** | Verify the repository ID with `arc repo list`. Make sure you've added the repository with `arc repo add`. |
| **"No results found across repositories"** | Check that you've set active repositories with `arc repo active` or specified repo_ids in your query. |
| **"Repository already exists"** | If you're trying to add the same repository twice, use `arc repo list` to see existing repositories. |
| **"Cross-repository relationships not showing"** | Ensure you've built all repositories and are querying with all relevant repository IDs. |

## API Reference

### SDK Methods

| Method | Description | Parameters | Return Value |
|--------|-------------|------------|--------------|
| `add_repository()` | Add a repository to the knowledge graph | `path`: Path to the repository<br>`name`: Repository name<br>`url`: Repository URL (optional)<br>`default_branch`: Default branch (optional) | Repository ID |
| `list_repositories()` | List all repositories in the knowledge graph | None | List of repository dictionaries |
| `build_repository()` | Build a specific repository | `repo_id`: Repository ID<br>`include_github`: Include GitHub data (optional)<br>`include_linear`: Include Linear data (optional) | Build result |
| `set_active_repositories()` | Set active repositories for queries | `repo_ids`: List of repository IDs | None |
| `get_active_repositories()` | Get the active repositories | None | List of repository dictionaries |
| `update_repository()` | Update repository information | `repo_id`: Repository ID<br>`new_path`: New local path (optional)<br>`new_name`: New repository name (optional)<br>`new_url`: New repository URL (optional)<br>`new_default_branch`: New default branch (optional) | Repository ID (may be new if path changed) |
| `remove_repository()` | Remove a repository from the knowledge graph | `repo_id`: Repository ID<br>`delete_nodes`: Whether to delete all nodes from this repository (optional) | Boolean indicating success |

### CLI Commands

| Command | Description | Options |
|---------|-------------|---------|
| `arc repo add` | Add a repository to the knowledge graph | `--name`: Repository name<br>`--url`: Repository URL (optional)<br>`--default-branch`: Default branch (optional) |
| `arc repo list` | List all repositories in the knowledge graph | `--json`: Output as JSON (optional) |
| `arc repo build` | Build a specific repository | `--github`: Include GitHub data (optional)<br>`--linear`: Include Linear data (optional) |
| `arc repo active` | Set active repositories for queries | None |
| `arc repo update` | Update repository information | `--path`: New local path<br>`--name`: New repository name<br>`--url`: New repository URL<br>`--default-branch`: New default branch |
| `arc repo remove` | Remove a repository from the knowledge graph | `--delete-nodes`: Delete all nodes from this repository<br>`--force`: Force removal without confirmation |
