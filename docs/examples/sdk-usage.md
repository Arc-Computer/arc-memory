# Using the Arc Memory SDK

This guide provides examples of how to use the Arc Memory SDK for core operations.

**Related Documentation:**
- [Building Graphs](./building-graphs.md) - Examples of building knowledge graphs
- [Tracing History](./tracing-history.md) - Examples of tracing history
- [Custom Plugins](./custom-plugins.md) - Creating custom data source plugins
- [API Documentation](../api/build.md) - API reference

## Basic SDK Usage

### Initializing the SDK

```python
from arc_memory.sql.db import init_db, get_node_count, get_edge_count
from pathlib import Path

# Initialize the database (default location)
conn = init_db()

# Or initialize with a specific path
db_path = Path("./my-graph.db")
conn = init_db(db_path)

# Get basic statistics
node_count = get_node_count(conn)
edge_count = get_edge_count(conn)

print(f"Knowledge graph contains {node_count} nodes and {edge_count} edges")
```

### Database Connection Handling

Arc Memory provides flexible connection handling that accepts either connection objects or paths:

```python
from arc_memory.sql.db import get_connection, ensure_connection, get_node_by_id
from pathlib import Path

# Method 1: Get a connection and use it
db_path = Path("./my-graph.db")
conn = get_connection(db_path)
node = get_node_by_id(conn, "node:123")

# Method 2: Use ensure_connection (accepts either connection or path)
# This is the recommended approach for flexible code
db_path = Path("./my-graph.db")
node = get_node_by_id(db_path, "node:123")  # Works with path directly

# You can also pass an existing connection
node = get_node_by_id(conn, "node:123")     # Works with connection

# Method 3: Use a context manager for automatic connection handling
from contextlib import closing
with closing(get_connection(db_path)) as conn:
    node = get_node_by_id(conn, "node:123")
    # Connection will be automatically closed when exiting the block
```

### Building a Knowledge Graph

```python
from arc_memory.build import build_graph
from pathlib import Path

# Build a knowledge graph for a repository
build_graph(
    repo_path=Path("./my-repo"),
    db_path=Path("./my-graph.db"),
    incremental=True,
    max_commits=1000,
    days=90,
    github_token="your-github-token"  # Optional
)
```

### Tracing History

```python
from arc_memory.trace import trace_history_for_file_line
from pathlib import Path

# Trace the history of a specific line in a file
history = trace_history_for_file_line(
    db_path=Path("./my-graph.db"),
    file_path="src/main.py",
    line_number=42,
    max_results=5,
    max_hops=3
)

# Print the history
for item in history:
    print(f"{item['type']}: {item['title']}")
    print(f"  {item['body'][:100]}...")
    print()
```

## Integration with CI/CD Pipelines

### GitHub Actions Workflow

```yaml
# .github/workflows/arc-memory.yml
name: Arc Memory

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

### Jenkins Pipeline

```groovy
pipeline {
    agent {
        docker {
            image 'python:3.10'
        }
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install arc-memory'
            }
        }

        stage('Build Graph') {
            steps {
                sh 'arc build --token ${GITHUB_TOKEN}'
            }
        }

        stage('Archive') {
            steps {
                archiveArtifacts artifacts: '~/.arc/graph.db.zst', fingerprint: true
            }
        }
    }
}
```

## Next Steps

- [Learn about building knowledge graphs](./building-graphs.md)
- [Explore tracing history examples](./tracing-history.md)
- [Create custom plugins](./custom-plugins.md)
- [Check the API documentation](../api/build.md)
