# ADR-001: Incremental Build Strategy

> Status: Accepted
>
> **Date:** 2025-04-25
> 
> **Decision makers:** Jarrod Barnes (Founder), Core Eng Team
> 
> **Context:** Arc Memory needs an efficient strategy for keeping the knowledge graph up-to-date without requiring full rebuilds. This ADR outlines the incremental build approach and CI integration.

## 1 · Problem Statement

The Arc Memory knowledge graph needs to stay current with repository changes, but rebuilding the entire graph for each update is inefficient and may hit GitHub API rate limits. We need a strategy that:

1. Minimizes GitHub API calls
2. Reduces build time for frequent updates
3. Integrates with CI/CD for team-wide graph updates
4. Maintains extensibility for future data sources

## 2 · Incremental Build Design

### 2.1 Build Manifest

The `build.json` manifest will be extended to include:

```json
{
  "node_count": 1234,
  "edge_count": 5678,
  "build_timestamp": "2025-04-25T14:30:00Z",
  "schema_version": "0.1.0",
  "last_commit_hash": "4f81a0b7e8d2c3f9...",
  "last_processed": {
    "git": {
      "commit_count": 500,
      "last_commit_hash": "4f81a0b7e8d2c3f9...",
      "timestamp": "2025-04-25T14:30:00Z"
    },
    "github": {
      "pr_count": 50,
      "issue_count": 75,
      "timestamp": "2025-04-25T14:30:00Z"
    },
    "adrs": {
      "adr_count": 10,
      "timestamp": "2025-04-25T14:30:00Z",
      "files": {
        "docs/adr/ADR-001.md": "2025-04-23T10:15:00Z"
      }
    }
  }
}
```

### 2.2 Incremental Processing Logic

#### Git Commits
- Use `git log <last_commit_hash>..HEAD` to get only new commits
- Process only these new commits and their associated files

#### GitHub API Calls
- Use GitHub's `since` parameter in API calls to fetch only PRs/issues updated after last build
- For issues, use `/issues?since=<last_build_timestamp>`
- For PRs, use `/pulls?state=all&sort=updated&direction=desc` and filter by update time

#### ADR Processing
- Track file modification times of ADRs
- Only reprocess ADRs that have been modified since last build

#### Database Updates
- Use SQLite transactions for atomic updates
- Add new nodes and edges without rebuilding the entire graph
- Update existing nodes if they've changed (e.g., PR status changed from open to merged)

## 3 · CI Integration

### 3.1 GitHub Actions Workflow

```yaml
name: Update Arc Memory Graph

on:
  push:
    branches: [main, master]
  pull_request:
    types: [opened, synchronize, closed]
  issues:
    types: [opened, edited, closed]

jobs:
  update-graph:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Need full history for git log
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install arc-memory
        run: pip install arc-memory
      
      - name: Download previous graph
        uses: actions/download-artifact@v3
        with:
          name: arc-memory-graph
          path: ~/.arc/
        continue-on-error: true  # First run won't have an artifact
      
      - name: Update graph
        run: arc build --incremental
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Upload updated graph
        uses: actions/upload-artifact@v3
        with:
          name: arc-memory-graph
          path: ~/.arc/graph.db.zst
```

### 3.2 Developer Workflow

1. Initial setup:
   ```bash
   pip install arc-memory
   arc auth gh
   arc build  # Initial full build
   ```

2. Regular updates:
   ```bash
   # Option 1: Pull latest CI-built graph
   arc build --pull
   
   # Option 2: Update locally
   arc build --incremental
   ```

## 4 · Extensibility for Future Integrations

### 4.1 Plugin Architecture

We will implement a plugin architecture for ingestors:

```python
class IngestorPlugin(Protocol):
    def get_name(self) -> str: ...
    def get_node_types(self) -> list[str]: ...
    def get_edge_types(self) -> list[str]: ...
    def ingest(self, last_processed: dict) -> tuple[list[Node], list[Edge], dict]: ...

class IngestorRegistry:
    def __init__(self):
        self.ingestors = {}
    
    def register(self, ingestor: IngestorPlugin):
        self.ingestors[ingestor.get_name()] = ingestor
```

This will allow for easy addition of new data sources like GitLab, Jira, etc.

### 4.2 Schema Versioning

We will include schema version in the database and implement migration paths for schema updates:

```python
def check_schema_compatibility(db_version: str, code_version: str) -> bool:
    # Simple semver check
    db_major, db_minor, _ = db_version.split('.')
    code_major, code_minor, _ = code_version.split('.')
    
    # Major version must match, minor version in DB must be <= code minor version
    return db_major == code_major and int(db_minor) <= int(code_minor)
```

## 5 · Decision

We will adopt the incremental build strategy with CI integration as described above. This approach balances efficiency with extensibility while maintaining the local-first philosophy of Arc Memory.

**Accepted** – 2025-04-25

— Jarrod Barnes

## 6 · Implementation Checklist

- [x] Extend `build.json` manifest schema
- [x] Implement `--incremental` flag in `arc build` command
- [x] Add incremental processing logic for Git data
- [x] Add incremental processing logic for GitHub data
- [x] Add incremental processing logic for ADRs
- [x] Implement schema version checking
- [ ] Create GitHub Actions workflow template
- [ ] Implement `--pull` flag to fetch CI-built graphs
- [ ] Create plugin architecture for ingestors
- [ ] Implement database migrations
