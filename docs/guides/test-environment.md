# Setting Up a Test Environment

This guide provides instructions for setting up a test environment for Arc Memory SDK, which is useful for development, testing, and integration with other systems.

**Related Documentation:**
- [Dependencies Guide](./dependencies.md) - Complete list of dependencies
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
- [Custom Plugins](../examples/custom-plugins.md) - Creating custom data source plugins

## Why Use a Test Environment?

A test environment allows you to:

1. Develop and test code that uses Arc Memory SDK without affecting your production environment
2. Test with mock data instead of real repositories
3. Run tests faster without network or database operations
4. Develop custom plugins without a full setup
5. Integrate with other systems in a controlled environment

## Setting Up a Virtual Environment

It's recommended to use a virtual environment to isolate your test environment from your system Python installation:

```bash
# Create a virtual environment
python -m venv arc-memory-test
cd arc-memory-test

# Activate the virtual environment
# On Unix/macOS:
source bin/activate
# On Windows:
.\Scripts\activate

# Install Arc Memory SDK with test dependencies
pip install arc-memory[test]
```

## Using Test Mode

Arc Memory SDK includes a test mode that allows you to run without connecting to an actual database. This is useful for testing and development:

```python
from arc_memory.sql.db import init_db

# Initialize the database in test mode
conn = init_db(test_mode=True)

# Use the connection as normal
from arc_memory.sql.db import get_node_count
node_count = get_node_count(conn)  # Returns 0 for a new test database
```

### Adding Test Data

You can add test data to the mock database:

```python
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel
from arc_memory.sql.db import add_nodes_and_edges
from datetime import datetime

# Create test nodes
nodes = [
    Node(
        id="commit:test1",
        type=NodeType.COMMIT,
        title="Test commit",
        body="This is a test commit",
        ts=datetime.now(),
        extra={"author": "Test User"}
    ),
    Node(
        id="pr:test1",
        type=NodeType.PR,
        title="Test PR",
        body="This is a test PR",
        ts=datetime.now(),
        extra={"author": "Test User"}
    )
]

# Create test edges
edges = [
    Edge(
        src="pr:test1",
        dst="commit:test1",
        rel=EdgeRel.MERGES,
        properties={"merged_at": datetime.now().isoformat()}
    )
]

# Add nodes and edges to the test database
add_nodes_and_edges(conn, nodes, edges)
```

## Setting Up a Test Repository

For more realistic testing, you can create a test Git repository:

```bash
# Create a test repository
mkdir test-repo
cd test-repo
git init

# Create some test files
echo "# Test Repository" > README.md
mkdir src
echo "def hello_world():\n    return 'Hello, World!'" > src/main.py

# Commit the files
git add .
git commit -m "Initial commit"

# Create a branch and make changes
git checkout -b feature-branch
echo "def goodbye_world():\n    return 'Goodbye, World!'" >> src/main.py
git add .
git commit -m "Add goodbye_world function"

# Return to main branch
git checkout main
```

## Testing with Mock GitHub Data

To test GitHub integration without actual GitHub API calls:

```python
import json
from arc_memory.plugins.github import GitHubIngestor
from unittest.mock import patch

# Mock GitHub API responses
mock_pr_response = {
    "number": 1,
    "title": "Test PR",
    "body": "This is a test PR",
    "user": {"login": "test-user"},
    "created_at": "2025-04-01T12:00:00Z",
    "merged_at": "2025-04-02T12:00:00Z",
    "html_url": "https://github.com/test/repo/pull/1"
}

# Use patch to mock the GitHub API
with patch('arc_memory.plugins.github.GitHubIngestor._get_prs') as mock_get_prs:
    mock_get_prs.return_value = [mock_pr_response]
    
    # Create the ingestor
    ingestor = GitHubIngestor(repo_path="test-repo", token="fake-token")
    
    # Ingest data
    nodes, edges, metadata = ingestor.ingest()
    
    # Verify the results
    assert len(nodes) > 0
    assert len(edges) > 0
```

## Testing with pytest

Arc Memory SDK includes a pytest fixture for testing with a mock database:

```python
# test_example.py
import pytest
from arc_memory.sql.db import init_db, add_nodes_and_edges
from arc_memory.schema.models import Node, NodeType

@pytest.fixture
def test_db():
    """Fixture for a test database."""
    return init_db(test_mode=True)

def test_node_count(test_db):
    """Test getting node count."""
    # Add a test node
    nodes = [
        Node(
            id="test:1",
            type=NodeType.COMMIT,
            title="Test",
            body="Test body",
            ts=None,
            extra={}
        )
    ]
    add_nodes_and_edges(test_db, nodes, [])
    
    # Test node count
    from arc_memory.sql.db import get_node_count
    assert get_node_count(test_db) == 1
```

Run the test with:

```bash
pytest test_example.py -v
```

## Testing the CLI

To test the CLI in a controlled environment:

```bash
# Set a custom database path
export ARC_DB_PATH=./test-graph.db

# Run CLI commands
arc build --debug
arc doctor
arc trace file src/main.py 1
```

## Continuous Integration

For CI/CD pipelines, you can use the test mode to run tests without a real database:

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install arc-memory[test]
      - name: Run tests
        run: |
          pytest tests/
```

## Next Steps

- [Learn about common errors and solutions](./troubleshooting.md)
- [Create custom plugins](../examples/custom-plugins.md)
- [Explore the API documentation](../api/build.md)
