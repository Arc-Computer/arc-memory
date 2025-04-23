> Status Proposed
>
> **Date** 25 Apr 2025
> 
> **Decision makers** Jarrod Barnes (Founder), Core Eng Team
> 
> **Context** Arc Memory needs an efficient strategy for keeping the knowledge graph up-to-date without requiring full rebuilds. This ADR outlines the incremental build approach and CI integration.

---

## 1 · Problem Statement

The Arc Memory knowledge graph needs to stay current with repository changes, but rebuilding the entire graph for each update is inefficient and may hit GitHub API rate limits. We need a strategy that:

1. Minimizes GitHub API calls
2. Reduces build time for frequent updates
3. Integrates with CI/CD for team-wide graph updates
4. Maintains extensibility for future data sources

---

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
    "commits": {
      "timestamp": "2025-04-25T14:30:00Z",
      "count": 500
    },
    "prs": {
      "timestamp": "2025-04-25T14:30:00Z",
      "latest_id": 123,
      "count": 50
    },
    "issues": {
      "timestamp": "2025-04-25T14:30:00Z",
      "latest_id": 456,
      "count": 75
    },
    "adrs": {
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
```python
def get_new_commits(last_commit_hash):
    # Only fetch commits since the last processed commit
    if last_commit_hash:
        return repo.git.log(f"{last_commit_hash}..HEAD", reverse=True)
    else:
        # Fall back to full build with limits
        return repo.git.log("--max-count=5000", "--since=1 year ago", reverse=True)
```

#### GitHub PRs
```python
def get_new_prs(last_timestamp):
    # Use GitHub's since parameter to get only updated PRs
    if last_timestamp:
        return github.get(f"/repos/{owner}/{repo}/pulls?state=all&sort=updated&direction=desc&since={last_timestamp}")
    else:
        # Fall back to full fetch with pagination
        return github.get_all_pages(f"/repos/{owner}/{repo}/pulls?state=all&sort=updated&direction=desc")
```

#### Issues
```python
def get_new_issues(last_timestamp):
    # Use GitHub's since parameter for issues
    if last_timestamp:
        return github.get(f"/repos/{owner}/{repo}/issues?state=all&since={last_timestamp}")
    else:
        # Fall back to full fetch with pagination
        return github.get_all_pages(f"/repos/{owner}/{repo}/issues?state=all")
```

#### ADRs
```python
def get_modified_adrs(last_processed_adrs):
    all_adrs = glob.glob("**/adr/**/*.md")
    if not last_processed_adrs:
        return all_adrs
    
    modified_adrs = []
    for adr_path in all_adrs:
        mtime = os.path.getmtime(adr_path)
        mtime_iso = datetime.fromtimestamp(mtime).isoformat()
        
        # If file is new or modified since last build
        if adr_path not in last_processed_adrs or mtime_iso > last_processed_adrs[adr_path]:
            modified_adrs.append(adr_path)
    
    return modified_adrs
```

### 2.3 Database Updates

```python
def update_graph_incrementally(new_nodes, new_edges):
    with sqlite3.connect("graph.db") as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        try:
            # Insert new nodes (ignore if already exists)
            for node in new_nodes:
                conn.execute(
                    "INSERT OR REPLACE INTO nodes(id, type, title, body, extra) VALUES(?, ?, ?, ?, ?)",
                    (node.id, node.type, node.title, node.body, json.dumps(node.extra))
                )
            
            # Insert new edges (ignore if already exists)
            for edge in new_edges:
                conn.execute(
                    "INSERT OR IGNORE INTO edges(src, dst, rel) VALUES(?, ?, ?)",
                    (edge.src, edge.dst, edge.rel)
                )
            
            # Update FTS index
            conn.execute("INSERT INTO fts_nodes(fts_nodes) VALUES('rebuild')")
            
            # Commit transaction
            conn.execute("COMMIT")
        except Exception as e:
            conn.execute("ROLLBACK")
            raise e
```

---

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

---

## 4 · Extensibility for Future Integrations

### 4.1 Plugin Architecture

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
    
    def get_ingestor(self, name: str) -> Optional[IngestorPlugin]:
        return self.ingestors.get(name)
    
    def get_all_ingestors(self) -> list[IngestorPlugin]:
        return list(self.ingestors.values())

# Usage
registry = IngestorRegistry()
registry.register(GitIngestor())
registry.register(GitHubIngestor())
registry.register(ADRIngestor())

# Future
registry.register(GitLabIngestor())
registry.register(JiraIngestor())
```

### 4.2 Schema Versioning

```python
def check_schema_compatibility(db_version: str, code_version: str) -> bool:
    # Simple semver check for now
    db_major, db_minor, _ = db_version.split('.')
    code_major, code_minor, _ = code_version.split('.')
    
    # Major version must match, minor version in DB must be <= code minor version
    return db_major == code_major and int(db_minor) <= int(code_minor)

def migrate_schema_if_needed(conn, from_version: str, to_version: str):
    if from_version == to_version:
        return
    
    # Apply migrations based on version differences
    if from_version == "0.1.0" and to_version == "0.2.0":
        # Example migration
        conn.execute("ALTER TABLE nodes ADD COLUMN updated_at TEXT")
```

---

## 5 · Decision

*Adopt the incremental build strategy with CI integration as described above. This approach balances efficiency with extensibility while maintaining the local-first philosophy of Arc Memory.*

**Proposed** – 25 Apr 2025

---

## 6 · Implementation Checklist

- [ ] Extend `build.json` manifest schema
- [ ] Implement `--incremental` flag in `arc build` command
- [ ] Add incremental processing logic for all data sources
- [ ] Create plugin architecture for ingestors
- [ ] Implement schema version checking and migrations
- [ ] Add GitHub Actions workflow template
- [ ] Implement `--pull` flag to fetch CI-built graphs
- [ ] Update documentation with incremental build guidance
