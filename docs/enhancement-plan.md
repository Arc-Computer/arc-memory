# Enhancing Arc Memory's Knowledge Graph Capabilities

This document outlines a comprehensive plan to enhance Arc Memory's knowledge graph capabilities to provide richer context for LLM reasoning. The plan focuses on three key areas: enhanced metadata extraction, deeper semantic analysis, and improved temporal modeling.

## 1. Enhanced Metadata Extraction

The current implementation extracts basic metadata but lacks depth in semantic understanding. Here are specific enhancements:

### 1.1. Create a Code Analysis Plugin

```python
class CodeAnalysisIngestor:
    """Ingestor plugin for deep code analysis."""

    def get_name(self) -> str:
        return "code_analysis"

    def get_node_types(self) -> List[str]:
        return [NodeType.FUNCTION, NodeType.CLASS, NodeType.MODULE]

    def get_edge_types(self) -> List[str]:
        return [EdgeRel.CONTAINS, EdgeRel.CALLS, EdgeRel.IMPORTS, EdgeRel.INHERITS_FROM]
```

This plugin would:
- Parse code files to extract functions, classes, and modules
- Analyze function signatures, docstrings, and parameter types
- Extract class hierarchies and method relationships
- Create fine-grained nodes for code entities rather than just file-level nodes

### 1.2. Extend the Schema Model

Add new node types to `NodeType` enum in `arc_memory/schema/models.py`:

```python
class NodeType(str, Enum):
    # Existing types
    COMMIT = "commit"
    FILE = "file"
    PR = "pr"
    ISSUE = "issue"
    ADR = "adr"
    
    # New types for code entities
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    COMPONENT = "component"
    SERVICE = "service"
```

Add new edge relationships to `EdgeRel` enum:

```python
class EdgeRel(str, Enum):
    # Existing relationships
    MODIFIES = "MODIFIES"
    MERGES = "MERGES"
    MENTIONS = "MENTIONS"
    DECIDES = "DECIDES"
    DEPENDS_ON = "DEPENDS_ON"
    
    # New relationships for code structure
    CONTAINS = "CONTAINS"
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    INHERITS_FROM = "INHERITS_FROM"
    IMPLEMENTS = "IMPLEMENTS"
    PART_OF = "PART_OF"
```

### 1.3. Enhance the Git Ingestor

The current Git ingestor (`arc_memory/ingest/git.py`) only creates basic file nodes. Enhance it to:

- Extract language-specific metadata based on file extensions
- Analyze code complexity metrics (cyclomatic complexity, lines of code)
- Track file change frequency and patterns over time
- Identify high-churn files and potential hotspots

## 2. Deeper Semantic Analysis

### 2.1. Create a Documentation Analysis Plugin

```python
class DocAnalysisIngestor:
    """Ingestor plugin for documentation analysis."""

    def get_name(self) -> str:
        return "doc_analysis"

    def get_node_types(self) -> List[str]:
        return [NodeType.DOCUMENT, NodeType.CONCEPT, NodeType.REQUIREMENT]

    def get_edge_types(self) -> List[str]:
        return [EdgeRel.DESCRIBES, EdgeRel.IMPLEMENTS, EdgeRel.REFERENCES]
```

This plugin would:
- Parse documentation files (Markdown, RST, etc.)
- Extract key concepts, requirements, and design decisions
- Link documentation to code entities
- Create a semantic layer over the codebase

### 2.2. Implement Natural Language Processing

Add NLP capabilities to extract semantic meaning from:
- Commit messages
- PR descriptions
- Issue discussions
- Documentation
- Code comments and docstrings

This could be implemented as a post-processing step in the build process:

```python
def enhance_with_nlp(nodes: List[Node], edges: List[Edge]) -> Tuple[List[Node], List[Edge]]:
    """Enhance nodes and edges with NLP-derived semantic information."""
    # Process text content with NLP
    # Extract entities, topics, and sentiment
    # Add semantic metadata to nodes
    # Create new semantic edges
    return enhanced_nodes, enhanced_edges
```

### 2.3. Add Architecture Detection

Implement heuristics to detect architectural patterns:
- Identify service boundaries based on directory structure and imports
- Detect design patterns in code
- Recognize architectural styles (microservices, monolith, etc.)
- Map dependencies between components

## 3. Enhanced Temporal Modeling

### 3.1. Create a Change Pattern Analyzer

```python
class ChangePatternIngestor:
    """Ingestor plugin for analyzing change patterns over time."""

    def get_name(self) -> str:
        return "change_patterns"

    def get_node_types(self) -> List[str]:
        return [NodeType.CHANGE_PATTERN, NodeType.REFACTORING]

    def get_edge_types(self) -> List[str]:
        return [EdgeRel.FOLLOWS, EdgeRel.PRECEDES, EdgeRel.CORRELATES_WITH]
```

This plugin would:
- Analyze commit history to identify patterns of change
- Detect refactoring operations
- Identify co-changing files and modules
- Track the evolution of components over time

### 3.2. Implement Temporal Queries

Enhance the database schema to support efficient temporal queries:

```python
def create_temporal_indices(conn: Any) -> None:
    """Create indices for efficient temporal queries."""
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_nodes_ts ON nodes(ts)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_edges_timestamp ON edges(
            json_extract(properties, '$.timestamp')
        )
        """
    )
```

### 3.3. Add Developer Workflow Analysis

Analyze commit patterns to understand developer workflows:
- Identify work patterns (time of day, days of week)
- Detect collaboration patterns between developers
- Map expertise areas based on file ownership
- Track knowledge transfer between team members

## 4. Implementation Strategy

Rather than rebuilding from scratch, we recommend an incremental approach:

### 4.1. Create New Plugins

Leverage the existing plugin architecture to add new ingestors without modifying the core build process:

1. Implement the new ingestors as separate plugins
2. Register them in the plugin discovery process
3. Enable them with command-line flags

### 4.2. Extend the Database Schema

The current SQLite schema is flexible but could be enhanced:

```python
def enhance_db_schema(conn: Any) -> None:
    """Enhance the database schema for richer metadata."""
    # Add new indices for efficient queries
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)
        """
    )
    
    # Add full-text search capabilities
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_nodes USING fts5(
            id, title, body, extra,
            content=nodes
        )
        """
    )
```

### 4.3. Add Post-Processing Steps

Modify the build process to include post-processing steps:

```python
def build_graph(
    repo_path: Path,
    output_path: Optional[Path] = None,
    max_commits: int = 5000,
    days: int = 365,
    incremental: bool = False,
    pull: bool = False,
    token: Optional[str] = None,
    linear: bool = False,
    debug: bool = False,
    enable_semantic_analysis: bool = True,
    enable_temporal_analysis: bool = True,
) -> None:
    # ... existing build process ...
    
    # Post-processing steps
    if enable_semantic_analysis:
        all_nodes, all_edges = enhance_with_semantic_analysis(all_nodes, all_edges)
    
    if enable_temporal_analysis:
        all_nodes, all_edges = enhance_with_temporal_analysis(all_nodes, all_edges)
    
    # ... continue with database operations ...
```

## 5. Specific Code Changes

Here are the specific files that need to be modified:

### 5.1. `arc_memory/schema/models.py`

- Add new node types and edge relationships
- Create new node classes for code entities
- Enhance the `Node` base class with additional metadata fields

### 5.2. `arc_memory/sql/db.py`

- Enhance the database schema
- Add indices for efficient queries
- Implement full-text search capabilities
- Add functions for temporal queries

### 5.3. `arc_memory/cli/build.py`

- Add new command-line options for enhanced analysis
- Implement post-processing steps
- Update progress reporting for new analysis steps

### 5.4. New Ingestor Plugins

- Create new files in `arc_memory/ingest/` for each new plugin
- Implement the `IngestorPlugin` protocol
- Register the plugins in `arc_memory/plugins.py`

## 6. Conclusion

By enhancing the Arc Memory build process with richer metadata extraction, deeper semantic analysis, and improved temporal modeling, we can create a knowledge graph that provides significantly more value for LLM reasoning. These enhancements build on the existing architecture rather than requiring a complete rebuild, allowing for incremental improvements while maintaining backward compatibility.

The resulting knowledge graph will provide:

1. **Rich Semantic Context**: Detailed information about code entities, their relationships, and their purpose
2. **Deep Reasoning Paths**: Support for multi-hop reasoning across different types of entities
3. **Temporal Understanding**: Insights into how code evolves over time and patterns of change
4. **Architectural Awareness**: Understanding of system architecture, component boundaries, and dependencies

These enhancements will enable LLMs to provide much more valuable insights when reasoning over the codebase, significantly outperforming vector-based approaches by leveraging the rich structure and semantics of the knowledge graph.
