# Enhancing Arc Memory's Knowledge Graph Capabilities

This document outlines a comprehensive plan to enhance Arc Memory's knowledge graph capabilities to provide richer context for LLM reasoning. The plan focuses on four key areas: enhanced metadata extraction, deeper semantic analysis, improved temporal modeling, and advanced reasoning structures. These enhancements are designed to optimize the JSON payload exported for LLM reasoning, ensuring it contains the rich context needed for sophisticated analysis.

> **Note:** This plan incorporates the latest research from 2024-2025 in Graph RAG, Knowledge Graph of Thoughts (KGoT), and temporal knowledge graph reasoning to ensure Arc Memory remains at the cutting edge of knowledge graph-based code reasoning.

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

### 1.4. Add Specialized Code Embeddings

Based on the 2025 paper "Enhancing Repository-Level Software Repair," incorporate specialized code embeddings:

```python
def enhance_with_code_embeddings(nodes: List[Node]) -> List[Node]:
    """Enhance nodes with specialized code embeddings."""
    # Load code embedding model (e.g., jina-embeddings-v2-base-code)
    # Generate embeddings for code entities
    # Store embeddings in node metadata for semantic similarity
    return enhanced_nodes
```

These embeddings will be included in the JSON payload to enable semantic similarity comparisons between code entities, significantly enhancing the LLM's ability to understand code relationships beyond explicit links.

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

### 2.4. Multi-Hop Reasoning Path Generation

Based on recent research in multi-hop reasoning over knowledge graphs, implement explicit reasoning path generation:

```python
class ReasoningPathGenerator:
    """Generate explicit reasoning paths for multi-hop queries."""

    def generate_paths(self, query_type: str, nodes: List[Node], edges: List[Edge]) -> List[Dict]:
        """Generate reasoning paths for common query types."""
        # Define common reasoning patterns (e.g., "impact analysis", "dependency chain")
        # Generate potential reasoning paths between entities
        # Score and rank reasoning paths
        # Include paths in the JSON payload
        return reasoning_paths
```

These pre-computed reasoning paths will be included in the JSON payload, providing the LLM with explicit guidance on how to traverse the knowledge graph for common reasoning tasks. This significantly improves the LLM's ability to perform complex multi-hop reasoning without having to discover these paths itself.

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

### 3.4. Dynamic Adaptation for Temporal Reasoning

Based on the 2024 NeurIPS paper "Large Language Models-guided Dynamic Adaptation for Temporal Knowledge Graph Reasoning," implement:

```python
def enhance_temporal_reasoning(nodes: List[Node], edges: List[Edge]) -> Tuple[List[Node], List[Edge]]:
    """Enhance temporal reasoning with dynamic adaptation."""
    # Identify temporal patterns in the graph
    # Create meta-edges that represent temporal reasoning paths
    # Add temporal context to the JSON payload
    return enhanced_nodes, enhanced_edges
```

This enhancement will add explicit temporal reasoning structures to the JSON payload, helping the LLM understand how code entities evolve over time and the causal relationships between changes.

## 4. Advanced Reasoning Structures

### 4.1. Knowledge Graph of Thoughts (KGoT) Integration

Based on the 2025 research on "Knowledge Graph of Thoughts," implement a KGoT processor:

```python
class KGoTProcessor:
    """Processor that implements Knowledge Graph of Thoughts."""

    def process(self, nodes: List[Node], edges: List[Edge]) -> Tuple[List[Node], List[Edge]]:
        """Generate a reasoning graph structure."""
        # Identify key decision points in the codebase
        # Create reasoning nodes that represent potential thought processes
        # Connect reasoning nodes to evidence nodes in the knowledge graph
        # Include these structures in the JSON payload
        return enhanced_nodes, enhanced_edges
```

This enhancement externalizes reasoning processes into the knowledge graph itself, providing the LLM with pre-computed reasoning structures that significantly improve its ability to explain decisions and understand code rationale.

### 4.2. GraphRAG Integration

Based on Microsoft Research's GraphRAG approach (2024), implement:

```python
def enhance_with_graphrag(nodes: List[Node], edges: List[Edge]) -> Dict[str, Any]:
    """Enhance the JSON payload with GraphRAG structures."""
    # Identify key retrieval points in the graph
    # Create graph-aware retrieval paths
    # Add retrieval metadata to the JSON payload
    return enhanced_payload
```

This enhancement optimizes the JSON payload for retrieval-augmented generation, helping the LLM efficiently navigate the knowledge graph during reasoning.

## 5. Implementation Strategy

Rather than rebuilding from scratch, we recommend an incremental approach:

### 5.1. Create New Plugins

Leverage the existing plugin architecture to add new ingestors without modifying the core build process:

1. Implement the new ingestors as separate plugins
2. Register them in the plugin discovery process
3. Enable them with command-line flags

### 5.2. Extend the Database Schema

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

### 5.3. Add Post-Processing Steps

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
    enable_reasoning_structures: bool = True,
) -> None:
    # ... existing build process ...

    # Post-processing steps
    if enable_semantic_analysis:
        all_nodes, all_edges = enhance_with_semantic_analysis(all_nodes, all_edges)

    if enable_temporal_analysis:
        all_nodes, all_edges = enhance_with_temporal_analysis(all_nodes, all_edges)

    if enable_reasoning_structures:
        all_nodes, all_edges = enhance_with_reasoning_structures(all_nodes, all_edges)

    # ... continue with database operations ...
```

### 5.4. Optimize JSON Payload Structure

Enhance the export functionality to optimize the JSON payload for LLM reasoning:

```python
def optimize_export_for_llm(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Optimize the export data structure for LLM reasoning."""
    # Add reasoning paths section
    export_data["reasoning_paths"] = generate_common_reasoning_paths(export_data)

    # Add semantic context section
    export_data["semantic_context"] = extract_semantic_context(export_data)

    # Add temporal patterns section
    export_data["temporal_patterns"] = extract_temporal_patterns(export_data)

    # Add thought structures section
    export_data["thought_structures"] = generate_thought_structures(export_data)

    return export_data
```

## 6. Specific Code Changes

Here are the specific files that need to be modified:

### 6.1. `arc_memory/schema/models.py`

- Add new node types and edge relationships
- Create new node classes for code entities
- Enhance the `Node` base class with additional metadata fields
- Add reasoning structure models

### 6.2. `arc_memory/sql/db.py`

- Enhance the database schema
- Add indices for efficient queries
- Implement full-text search capabilities
- Add functions for temporal queries

### 6.3. `arc_memory/cli/build.py`

- Add new command-line options for enhanced analysis
- Implement post-processing steps
- Update progress reporting for new analysis steps
- Add options for enabling/disabling specific enhancements

### 6.4. `arc_memory/export.py`

- Enhance the export functionality to optimize the JSON payload
- Implement the `optimize_export_for_llm` function
- Add reasoning paths, semantic context, and temporal patterns to the export
- Structure the JSON payload for efficient LLM reasoning

### 6.5. New Ingestor Plugins

- Create new files in `arc_memory/ingest/` for each new plugin:
  - `arc_memory/ingest/code_analysis.py`
  - `arc_memory/ingest/doc_analysis.py`
  - `arc_memory/ingest/change_patterns.py`
- Implement the `IngestorPlugin` protocol
- Register the plugins in `arc_memory/plugins.py`

### 6.6. New Processing Modules

- Create new files for post-processing:
  - `arc_memory/process/semantic_analysis.py`
  - `arc_memory/process/temporal_analysis.py`
  - `arc_memory/process/reasoning_structures.py`
  - `arc_memory/process/kgot.py`
- Implement the processing functions
- Register the processors in the build process

## 7. Conclusion

By enhancing the Arc Memory build process with richer metadata extraction, deeper semantic analysis, improved temporal modeling, and advanced reasoning structures, we can create a knowledge graph that provides significantly more value for LLM reasoning. These enhancements build on the existing architecture rather than requiring a complete rebuild, allowing for incremental improvements while maintaining backward compatibility.

The resulting JSON payload will provide:

1. **Rich Semantic Context**: Detailed information about code entities, their relationships, and their purpose
2. **Deep Reasoning Paths**: Pre-computed paths for multi-hop reasoning across different types of entities
3. **Temporal Understanding**: Insights into how code evolves over time and patterns of change
4. **Architectural Awareness**: Understanding of system architecture, component boundaries, and dependencies
5. **Reasoning Structures**: Knowledge Graph of Thoughts (KGoT) structures that externalize reasoning processes
6. **GraphRAG Optimization**: Structures that optimize retrieval-augmented generation over the knowledge graph

These enhancements will enable LLMs to provide much more valuable insights when reasoning over the codebase, significantly outperforming vector-based approaches by leveraging the rich structure and semantics of the knowledge graph.

## 8. LLM Integration in the Build Process

Based on our analysis, integrating LLMs directly into the build process will provide significant benefits while maintaining reasonable build times. We will use Ollama with the Phi-4 Mini Reasoning model (3.8B parameters) for all LLM-enhanced components.

### 8.1. LLM Integration Architecture

We will implement a tiered approach to LLM integration:

```python
def build_graph(
    repo_path: Path,
    output_path: Optional[Path] = None,
    llm_enhancement_level: str = "standard",  # "fast", "standard", or "deep"
    max_commits: int = 5000,
    days: int = 365,
    incremental: bool = False,
) -> None:
    """Build the knowledge graph with LLM enhancements."""
    # 1. Standard data collection (unchanged)
    all_nodes, all_edges = collect_data_from_plugins(
        repo_path, max_commits, days, incremental
    )

    # 2. Apply LLM enhancements based on selected level
    if llm_enhancement_level != "none":
        # Configure enhancement parameters based on level
        params = get_llm_enhancement_params(llm_enhancement_level)

        # Apply LLM enhancements
        all_nodes, all_edges = apply_llm_enhancements(
            all_nodes, all_edges, repo_path, params
        )

    # 3. Store in database (unchanged)
    store_graph_in_database(output_path, all_nodes, all_edges)
```

### 8.2. Specific LLM Enhancement Points

#### 8.2.1. Code Semantic Analysis

```python
def enhance_code_semantics(file_nodes: List[Node], file_contents: Dict[str, str]) -> List[Node]:
    """Enhance file nodes with semantic understanding of code using Phi-4 Mini."""
    # Batch files for efficient processing
    batches = create_batches(file_nodes, batch_size=15)

    for batch in batches:
        # Prepare prompt with code content
        prompt = create_code_analysis_prompt(batch, file_contents)

        # Call Phi-4 Mini via Ollama
        response = ollama.generate(
            model="phi4-mini-reasoning",
            prompt=prompt,
            options={"temperature": 0.1}
        )

        # Parse response and update nodes
        enhanced_nodes = parse_code_semantics(response, batch)

    return enhanced_nodes
```

#### 8.2.2. Relationship Inference

```python
def infer_relationships(nodes: List[Node], edges: List[Edge]) -> List[Edge]:
    """Infer implicit relationships between nodes using Phi-4 Mini."""
    # Select high-value node pairs for analysis
    candidate_pairs = select_candidate_pairs(nodes)

    # Batch processing for efficiency
    batches = create_batches(candidate_pairs, batch_size=20)

    inferred_edges = []
    for batch in batches:
        # Create prompt with node context
        prompt = create_relationship_inference_prompt(batch, nodes, edges)

        # Call Phi-4 Mini via Ollama
        response = ollama.generate(
            model="phi4-mini-reasoning",
            prompt=prompt,
            options={"temperature": 0.2}
        )

        # Parse response and create new edges
        new_edges = parse_inferred_relationships(response, batch)
        inferred_edges.extend(new_edges)

    return inferred_edges
```

#### 8.2.3. Knowledge Graph of Thoughts Generation

```python
def generate_kgot_structures(nodes: List[Node], edges: List[Edge]) -> Tuple[List[Node], List[Edge]]:
    """Generate Knowledge Graph of Thoughts structures using Phi-4 Mini."""
    # Identify key decision points in the codebase
    decision_points = identify_decision_points(nodes, edges)

    # Process each decision point
    thought_nodes = []
    thought_edges = []

    for point in decision_points:
        # Create prompt with decision context
        prompt = create_kgot_prompt(point, nodes, edges)

        # Call Phi-4 Mini via Ollama
        response = ollama.generate(
            model="phi4-mini-reasoning",
            prompt=prompt,
            options={"temperature": 0.3}
        )

        # Parse response and create thought structures
        new_nodes, new_edges = parse_kgot_structures(response, point)
        thought_nodes.extend(new_nodes)
        thought_edges.extend(new_edges)

    return thought_nodes, thought_edges
```

#### 8.2.4. Export Optimization

```python
def optimize_export_for_llm(export_data: Dict[str, Any]) -> Dict[str, Any]:
    """Optimize the export data structure for LLM reasoning using Phi-4 Mini."""
    # Create prompt with export data summary
    prompt = create_export_optimization_prompt(export_data)

    # Call Phi-4 Mini via Ollama
    response = ollama.generate(
        model="phi4-mini-reasoning",
        prompt=prompt,
        options={"temperature": 0.2}
    )

    # Parse response and enhance export data
    enhanced_export = parse_export_optimizations(response, export_data)

    return enhanced_export
```

### 8.3. Performance Optimization Strategies

To keep the build process under 60-90 seconds while integrating LLMs:

#### 8.3.1. Tiered Enhancement Levels

We will implement three enhancement levels:

1. **Fast Tier** (30-45 seconds):
   - Basic LLM enhancement for critical files only
   - Used for frequent developer builds

2. **Standard Tier** (60-90 seconds):
   - Comprehensive LLM enhancement
   - Used for daily/regular builds

3. **Deep Tier** (2-5 minutes):
   - Exhaustive LLM analysis of entire codebase
   - Used for weekly builds or major releases

#### 8.3.2. Batching and Parallelization

```python
def apply_llm_enhancements_parallel(nodes: List[Node], edges: List[Edge], params: Dict) -> Tuple[List[Node], List[Edge]]:
    """Apply LLM enhancements in parallel."""
    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as executor:
        # Submit semantic analysis task
        semantic_future = executor.submit(
            enhance_code_semantics,
            [n for n in nodes if n.type == NodeType.FILE],
            get_file_contents(repo_path, nodes),
            params["batch_size"]
        )

        # Submit relationship inference task
        relationship_future = executor.submit(
            infer_relationships,
            nodes,
            edges,
            params["max_pairs"]
        )

        # Submit KGoT generation task
        kgot_future = executor.submit(
            generate_kgot_structures,
            nodes,
            edges,
            params["max_decision_points"]
        )

        # Collect results
        enhanced_nodes = semantic_future.result()
        new_edges = relationship_future.result()
        thought_nodes, thought_edges = kgot_future.result()

        # Combine results
        all_nodes = merge_nodes(nodes, enhanced_nodes, thought_nodes)
        all_edges = edges + new_edges + thought_edges

        return all_nodes, all_edges
```

#### 8.3.3. Selective Processing

```python
def select_high_value_files(nodes: List[Node], repo_path: Path) -> List[Node]:
    """Select high-value files for LLM processing."""
    # Criteria for selection:
    # 1. Recently modified files
    # 2. Files with high connectivity in the graph
    # 3. Files in core directories
    # 4. Non-generated, non-test files

    high_value_files = []
    for node in nodes:
        if node.type != NodeType.FILE:
            continue

        # Check recency
        file_path = repo_path / node.path
        if file_path.exists() and is_recently_modified(file_path):
            high_value_files.append(node)
            continue

        # Check connectivity
        if get_node_connectivity(node, edges) > CONNECTIVITY_THRESHOLD:
            high_value_files.append(node)
            continue

        # Check if in core directory
        if is_in_core_directory(node.path):
            high_value_files.append(node)
            continue

        # Exclude generated/test files
        if is_generated_file(node.path) or is_test_file(node.path):
            continue

        # Add other high-value files based on heuristics
        if is_high_value_file(node.path):
            high_value_files.append(node)

    return high_value_files
```

### 8.4. Ollama Integration

We will integrate Ollama as follows:

```python
class OllamaClient:
    """Client for interacting with Ollama."""

    def __init__(self, host: str = "http://localhost:11434"):
        """Initialize the Ollama client."""
        self.host = host
        self.session = requests.Session()

    def generate(self, model: str, prompt: str, options: Dict = None) -> str:
        """Generate a response from Ollama."""
        url = f"{self.host}/api/generate"

        data = {
            "model": model,
            "prompt": prompt,
            "options": options or {}
        }

        response = self.session.post(url, json=data)
        response.raise_for_status()

        return response.json()["response"]

    def ensure_model_available(self, model: str) -> bool:
        """Ensure the specified model is available, pulling if needed."""
        url = f"{self.host}/api/show"

        try:
            response = self.session.post(url, json={"name": model})
            if response.status_code == 200:
                return True
        except:
            pass

        # Model not available, pull it
        print(f"Pulling model {model}...")
        url = f"{self.host}/api/pull"
        response = self.session.post(url, json={"name": model})

        # Wait for model to be pulled
        while True:
            data = response.json()
            if "error" in data:
                raise Exception(f"Error pulling model: {data['error']}")

            if data.get("status") == "success":
                return True

            time.sleep(1)
```

### 8.5. Build Process Integration

The LLM enhancements will be integrated into the build process with the following CLI options:

```python
@app.command()
def build(
    repo_path: Path = typer.Option(
        Path.cwd(), "--repo", "-r", help="Path to the Git repository."
    ),
    output_path: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Path to the output database file."
    ),
    max_commits: int = typer.Option(
        5000, "--max-commits", help="Maximum number of commits to process."
    ),
    days: int = typer.Option(
        365, "--days", help="Maximum age of commits to process in days."
    ),
    incremental: bool = typer.Option(
        False, "--incremental", help="Only process new data since last build."
    ),
    llm_enhancement: str = typer.Option(
        "standard", "--llm-enhancement", "-l",
        help="LLM enhancement level: none, fast, standard, deep."
    ),
    ollama_host: str = typer.Option(
        "http://localhost:11434", "--ollama-host",
        help="Ollama API host URL."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Build the knowledge graph with optional LLM enhancements."""
    # Implementation details...
```

This comprehensive LLM integration approach will significantly enhance the quality of the knowledge graph while maintaining reasonable build times of 60-90 seconds for standard builds.

## 9. CI Integration for PR Bot

The LLM-enhanced build process is designed to run entirely locally inside CI environments when a user downloads our PR bot. This ensures a seamless "two-click setup" experience while providing the full benefits of our advanced knowledge graph capabilities.

### 9.1. CI-Specific Mode

```python
def build_graph(
    # Existing parameters
    ci_mode: bool = False,
) -> None:
    """Build the knowledge graph with LLM enhancements."""
    # If in CI mode, use optimized parameters
    if ci_mode and llm_enhancement_level != "none":
        params = get_ci_optimized_params()
    else:
        params = get_llm_enhancement_params(llm_enhancement_level)

    # Rest of the function
```

### 9.2. Automatic Ollama Setup

```python
def ensure_ollama_available(model: str = "phi4-mini-reasoning") -> bool:
    """Ensure Ollama and the required model are available."""
    # Check if Ollama is installed
    if not shutil.which("ollama"):
        if is_ci_environment():
            # In CI, we can install Ollama automatically
            subprocess.run(["curl", "-fsSL", "https://ollama.com/install.sh"], stdout=subprocess.PIPE)
            subprocess.run(["sh"], input=subprocess.PIPE.stdout)
        else:
            raise RuntimeError("Ollama not found. Please install Ollama: https://ollama.com/download")

    # Check if model is available and pull if needed
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True
        )
        if model not in result.stdout:
            print(f"Pulling model {model}...")
            subprocess.run(["ollama", "pull", model])
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to ensure model availability: {e}")
```

### 9.3. CI-Optimized Parameters

```python
def get_ci_optimized_params() -> Dict[str, Any]:
    """Get optimized parameters for CI environments."""
    return {
        "batch_size": 20,  # Process more files per batch
        "max_pairs": 50,   # Limit relationship inference
        "max_decision_points": 5,  # Focus on key decision points only
        "parallel": True,  # Enable parallelization
        "timeout": 30,     # Set strict timeout for LLM calls
        "high_value_only": True,  # Process only high-value files
    }
```

### 9.4. GitHub Action Example

```yaml
name: Build Knowledge Graph

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
        fetch-depth: 0  # Get full history for proper graph building

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .

    - name: Install and start Ollama
      run: |
        curl -fsSL https://ollama.com/install.sh | sh
        ollama serve &
        sleep 5  # Give Ollama time to start

    - name: Cache Ollama models
      uses: actions/cache@v2
      with:
        path: ~/.ollama/models
        key: ollama-models-${{ runner.os }}-phi4-mini

    - name: Build knowledge graph
      run: |
        arc build --llm-enhancement fast --ci-mode

    - name: Export graph for PR
      run: |
        arc export ${{ github.sha }} --out pr-context.json

    - name: Upload PR context
      uses: actions/upload-artifact@v3
      with:
        name: pr-context
        path: pr-context.json
```

### 9.5. Complete CI Workflow

The complete workflow for the PR bot with LLM enhancements will be:

1. **Setup**: Automatically install Ollama and download the Phi-4 Mini model in CI
2. **Build**: Run the build process with CI-optimized parameters
3. **Export**: Generate the enhanced JSON payload for the PR
4. **Analyze**: Use the PR bot to analyze the enhanced knowledge graph
5. **Comment**: Add insights to the PR based on the analysis

This approach ensures that all users can benefit from our advanced LLM enhancements without any manual setup, maintaining our goal of a "two-click setup" experience.
