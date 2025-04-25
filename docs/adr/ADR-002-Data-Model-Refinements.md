# ADR-002: Data Model Refinements

> Status: Accepted
>
> **Date:** 2025-04-26
>
> **Decision makers:** Jarrod Barnes (Founder), Core Eng Team
>
> **Context:** After initial implementation of the data model, we identified several refinements needed to fully support the hover and trace-history features in Arc Memory.

## 1 · Problem Statement

The current data model is missing several key elements needed for efficient tracing of decision history:

1. There is no explicit `File` node type, making it difficult to connect file+line to modifying commits
2. Node attribute naming is inconsistent with the intended schema
3. Some attributes that should be optional are required
4. Edge direction standards are not explicitly defined
5. The build manifest structure is more complex than needed

These issues could impact the effectiveness of the hover and trace-history features, which are core to Arc Memory's value proposition.

## 2 · Proposed Changes

### 2.1 Add File Node Type

Add a dedicated `FileNode` class to represent files in the repository:

```python
class FileNode(Node):
    """A file in the repository."""
    type: NodeType = NodeType.FILE
    path: str
    language: Optional[str] = None
    last_modified: Optional[datetime] = None
```

This allows us to:
- Connect file+line to modifying commits via `MODIFIES` edges
- Store file-specific metadata (path, language, etc.)
- Establish a clear starting point for trace history queries

### 2.2 Rename `created_at` to `ts`

Rename the `created_at` field in the `Node` base class to `ts` for consistency:

```python
class Node(BaseModel):
    id: str
    type: NodeType
    title: Optional[str] = None
    body: Optional[str] = None
    ts: Optional[datetime] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
```

This provides a consistent timestamp field across all node types, which is essential for chronological ordering.

### 2.3 Make `title` and `body` Optional

Update the `Node` base class to make `title` and `body` optional with default values:

```python
title: Optional[str] = None
body: Optional[str] = None
```

This provides flexibility for nodes that might not have meaningful titles or bodies (e.g., some file types).

### 2.4 Ensure Consistent Edge Direction

Explicitly define and enforce a consistent edge direction standard:

- All edges stored in forward direction (`src → dst`)
- Commit → File uses `MODIFIES`
- PR → Commit uses `MERGES`
- Issue → Commit/PR uses `MENTIONS`
- ADR → Commit/File uses `DECIDES`

This simplifies SQL queries and the 2-hop BFS algorithm for trace history.

### 2.5 Simplify Build Manifest

Simplify the `BuildManifest` model to match the suggested structure:

```python
class BuildManifest(BaseModel):
    """Metadata about a graph build."""
    schema_version: str
    build_time: datetime
    commit: Optional[str] = None
    node_count: int
    edge_count: int
    # Additional fields for incremental builds
    last_processed: Dict[str, Any] = Field(default_factory=dict)
```

This provides the essential information while remaining simple and efficient.

## 3 · Alternatives Considered

### 3.1 Using Bidirectional Edges

We considered storing edges in both directions (e.g., both Commit → File and File → Commit) to simplify certain queries. However, this would:
- Double the number of edges in the database
- Increase storage requirements
- Complicate edge creation and maintenance
- Potentially introduce inconsistencies

By standardizing on forward direction and using appropriate queries, we can achieve the same functionality more efficiently.

### 3.2 Adding User Nodes

We considered adding a dedicated `UserNode` type to represent authors and contributors. However:
- It's not required for the decision-trail MVP
- Author information can be stored in `Commit.extra["author"]`
- It would add complexity to the schema
- It would require additional edges and queries

We can revisit this in a future version if needed for more advanced features.

## 4 · Impact

### 4.1 Positive Impacts

- Improved traceability from file+line to related commits, PRs, issues, and ADRs
- More efficient trace history queries
- Clearer and more consistent data model
- Better support for the hover feature
- Simplified build manifest

### 4.2 Negative Impacts

- Minor breaking changes to existing code
- Need to update any code that depends on the current model
- Slight increase in database size due to additional File nodes

## 5 · Decision

We will implement the proposed changes to the data model:

1. Add a `FileNode` class to represent files in the repository
2. Rename `created_at` to `ts` for consistency
3. Make `title` and `body` optional with default values
4. Ensure consistent edge direction across all relationship types
5. Simplify the build manifest structure

These changes will ensure our data model fully supports the core functionality while remaining simple and efficient.

**Accepted** – 2025-04-26

— Jarrod Barnes

## 6 · Implementation Checklist

- [ ] Update `NodeType` enum to include `FILE`
- [ ] Add `FileNode` class
- [ ] Rename `created_at` to `ts` in `Node` base class
- [ ] Make `title` and `body` optional with default values
- [ ] Update all node subclasses to use the new field names
- [ ] Ensure all edge creation follows the consistent direction standard
- [ ] Simplify the `BuildManifest` model
- [ ] Update database operations to handle File nodes
- [ ] Update ingestion logic to create File nodes
- [ ] Update tests to reflect the new model
