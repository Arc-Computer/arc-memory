# GitHub Integration

Arc Memory provides robust integration with GitHub to ingest data from repositories, including pull requests, issues, and related information. This document explains how to use the GitHub integration and how to query the resulting knowledge graph.

## Setup

To use the GitHub integration, you need to authenticate with GitHub. Arc Memory supports two authentication methods:

1. **Personal Access Token (PAT)**: You can provide a GitHub personal access token with the appropriate scopes.
2. **GitHub App**: Arc Memory can use a GitHub App installation token for authentication.

### Authentication with Personal Access Token

To authenticate with a personal access token:

```python
from arc_memory import ArcMemory

# Initialize Arc Memory with GitHub token
arc = ArcMemory(
    repo_path="path/to/your/repo",
    github_token="your-github-token"
)

# Build the knowledge graph
arc.build()
```

### Authentication with GitHub App

If you have a GitHub App installed on your repository, Arc Memory can use the installation token:

```python
from arc_memory import ArcMemory

# Initialize Arc Memory (it will automatically use the GitHub App token)
arc = ArcMemory(
    repo_path="path/to/your/repo"
)

# Build the knowledge graph
arc.build()
```

## Data Ingestion

When you build the knowledge graph, Arc Memory ingests the following data from GitHub:

- **Pull Requests**: Title, body, state, creation date, merge status, and more
- **Issues**: Title, body, state, creation date, labels, and more
- **Comments**: Comments on pull requests and issues
- **Reviews**: Pull request reviews and review comments
- **Commits**: Commit information for pull requests
- **Mentions**: User mentions in pull requests, issues, and comments

The ingestion process uses a hybrid approach:

1. **GraphQL API** for efficiently fetching core data (PRs, issues, etc.)
2. **REST API** for specific operations (PR files, commit details, etc.)

## Knowledge Graph Structure

The GitHub data is stored in the knowledge graph as nodes and edges:

### Nodes

- **PRNode**: Represents a pull request
- **IssueNode**: Represents an issue
- **CommitNode**: Represents a commit
- **FileNode**: Represents a file

### Edges

- **MENTIONS**: Connects a PR or issue to a user mentioned in it
- **REFERENCES**: Connects a PR to an issue it references
- **MODIFIES**: Connects a PR to a file it modifies
- **AUTHORED_BY**: Connects a PR or issue to its author
- **REVIEWED_BY**: Connects a PR to its reviewers

## Querying the Knowledge Graph

You can query the knowledge graph to find relationships between different entities:

### Finding Pull Requests by Author

```python
from arc_memory import ArcMemory

arc = ArcMemory(repo_path="path/to/your/repo")
prs = arc.query(
    node_type="PRNode",
    filters={"extra.author": "username"}
)

for pr in prs:
    print(f"PR #{pr.number}: {pr.title}")
```

### Finding Issues Mentioned in Pull Requests

```python
from arc_memory import ArcMemory

arc = ArcMemory(repo_path="path/to/your/repo")
pr = arc.query_one(
    node_type="PRNode",
    filters={"number": 123}
)

if pr:
    # Find issues mentioned in this PR
    mentioned_issues = arc.query_connected(
        src_id=pr.id,
        edge_rel="MENTIONS",
        dst_type="IssueNode"
    )
    
    for issue in mentioned_issues:
        print(f"Issue #{issue.number}: {issue.title}")
```

### Finding Files Modified by a Pull Request

```python
from arc_memory import ArcMemory

arc = ArcMemory(repo_path="path/to/your/repo")
pr = arc.query_one(
    node_type="PRNode",
    filters={"number": 123}
)

if pr:
    # Find files modified by this PR
    modified_files = arc.query_connected(
        src_id=pr.id,
        edge_rel="MODIFIES",
        dst_type="FileNode"
    )
    
    for file in modified_files:
        print(f"Modified file: {file.path}")
```

## Incremental Builds

Arc Memory supports incremental builds for GitHub data. When you run `arc.build()` after an initial build, it will only fetch new or updated data from GitHub, making the process much faster.

The incremental build uses the timestamp of the last build to fetch only the data that has changed since then:

```python
from arc_memory import ArcMemory

arc = ArcMemory(repo_path="path/to/your/repo")

# First build (fetches all data)
arc.build()

# Later builds (fetch only new or updated data)
arc.build()
```

## Rate Limiting

GitHub API has rate limits that Arc Memory respects. The integration includes:

- Tracking of remaining rate limits
- Exponential backoff for retries
- Sleep logic when approaching rate limits

If you encounter rate limit issues, you can:

1. Use a GitHub App installation token, which has higher rate limits
2. Reduce the scope of data fetching (e.g., limit to recent PRs)
3. Run builds during off-peak hours

## Troubleshooting

### Authentication Issues

If you encounter authentication issues:

1. Check that your token has the required scopes (`repo` for private repositories)
2. Ensure your token is not expired
3. Verify that you have access to the repository

### Rate Limit Issues

If you hit rate limits:

1. Check the error message for the reset time
2. Wait until the rate limit resets
3. Consider using a GitHub App installation token

### Missing Data

If some data is missing:

1. Check that you have access to the repository
2. Verify that the data exists in GitHub
3. Check for any error messages in the logs

## Advanced Configuration

You can configure the GitHub integration with additional options:

```python
from arc_memory import ArcMemory

arc = ArcMemory(
    repo_path="path/to/your/repo",
    github_token="your-github-token",
    github_options={
        "max_prs": 500,  # Maximum number of PRs to fetch
        "max_issues": 500,  # Maximum number of issues to fetch
        "include_closed": True,  # Include closed PRs and issues
        "fetch_comments": True,  # Fetch comments for PRs and issues
        "fetch_reviews": True,  # Fetch reviews for PRs
    }
)

arc.build()
```
