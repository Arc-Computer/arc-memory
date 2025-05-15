# Arc Memory SDK API Reference

Complete reference documentation for all Arc Memory SDK classes, methods, and return types.

## Core API

### Arc Class

The `Arc` class is the main entry point for interacting with Arc Memory.

```python
class Arc:
    """Main entry point for interacting with Arc Memory."""

    def __init__(
        self,
        repo_path: str,
        adapter_type: str = "sqlite",
        connection_params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Arc with a repository path and database adapter.

        Args:
            repo_path: Path to the repository
            adapter_type: Type of database adapter to use ("sqlite" or "neo4j")
            connection_params: Optional connection parameters for the database adapter
        """

    def query(
        self,
        question: str,
        max_results: int = 5,
        max_hops: int = 3,
        include_causal: bool = True,
        cache: bool = True
    ) -> QueryResult:
        """
        Query the knowledge graph with a natural language question.

        Args:
            question: The natural language question to ask
            max_results: Maximum number of results to return
            max_hops: Maximum number of hops to traverse in the graph
            include_causal: Whether to include causal relationships
            cache: Whether to use the cache

        Returns:
            QueryResult object containing the answer and evidence
        """

    def get_decision_trail(
        self,
        file_path: str,
        line_number: int,
        max_results: int = 5,
        max_hops: int = 3,
        include_rationale: bool = True,
        cache: bool = True
    ) -> List[DecisionTrailEntry]:
        """
        Get the decision trail for a specific line in a file.

        Args:
            file_path: Path to the file
            line_number: Line number to get the decision trail for
            max_results: Maximum number of results to return
            max_hops: Maximum number of hops to traverse in the graph
            include_rationale: Whether to include rationale for decisions
            cache: Whether to use the cache

        Returns:
            List of DecisionTrailEntry objects
        """

    def get_related_entities(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        direction: str = "both",
        max_results: int = 10,
        include_properties: bool = False,
        cache: bool = True
    ) -> List[RelatedEntity]:
        """
        Get entities related to a specific entity.

        Args:
            entity_id: ID of the entity to get related entities for
            relationship_types: Optional list of relationship types to filter by
            direction: Direction of relationships to include ("incoming", "outgoing", or "both")
            max_results: Maximum number of results to return
            include_properties: Whether to include relationship properties
            cache: Whether to use the cache

        Returns:
            List of RelatedEntity objects
        """

    def get_entity_details(
        self,
        entity_id: str,
        include_related: bool = False,
        cache: bool = True
    ) -> EntityDetails:
        """
        Get detailed information about an entity.

        Args:
            entity_id: ID of the entity to get details for
            include_related: Whether to include related entities
            cache: Whether to use the cache

        Returns:
            EntityDetails object
        """

    def analyze_component_impact(
        self,
        component_id: str,
        impact_types: Optional[List[str]] = None,
        max_depth: int = 3,
        cache: bool = True,
        callback: Optional[ProgressCallback] = None
    ) -> List[ImpactResult]:
        """
        Analyze the potential impact of changes to a component.

        This method identifies components that may be affected by changes to the
        specified component, based on historical co-change patterns and explicit
        dependencies in the knowledge graph. It helps predict the "blast radius"
        of changes, which is useful for planning refactoring efforts, assessing risk,
        and understanding the architecture of your codebase.

        Args:
            component_id: The ID of the component to analyze. This can be a file, directory,
                module, or any other component in your codebase. Format should be
                "type:identifier", e.g., "file:src/auth/login.py".
            impact_types: Types of impact to include in the analysis. Options are:
                - "direct": Components that directly depend on or are depended upon by the target
                - "indirect": Components connected through a chain of dependencies
                - "potential": Components that historically changed together with the target
                If None, all impact types will be included.
            max_depth: Maximum depth of indirect dependency analysis. Higher values will
                analyze more distant dependencies but may take longer. Values between
                2-5 are recommended for most codebases.
            cache: Whether to use cached results if available. When True (default),
                results are cached and retrieved from cache if a matching query exists.
                Set to False to force a fresh query execution.
            callback: Optional callback for progress reporting. If provided,
                it will be called at various stages of the analysis with progress updates.

        Returns:
            A list of ImpactResult objects representing affected components. Each result
            includes the component ID, type, title, impact type, impact score (0-1),
            and the path of dependencies from the target component.
        """

    def ensure_repository(self, name: Optional[str] = None) -> str:
        """
        Ensure a repository entry exists for the current repo_path.

        This method checks if a repository entry exists for the current repo_path,
        and creates one if it doesn't. It returns the repository ID.

        Args:
            name: Optional name for the repository. If None, uses the repo_path name.

        Returns:
            The repository ID.
        """

    def get_current_repository(self) -> Optional[Dict[str, Any]]:
        """
        Get the current repository based on repo_path.

        Returns:
            The repository as a dictionary, or None if it doesn't exist.
        """

    def build(
        self,
        repo_path=None,
        include_github=True,
        include_linear=False,
        include_architecture=True,
        use_llm=True,
        llm_provider="openai",
        llm_model="gpt-4.1",
        llm_enhancement_level="standard",
        verbose=False,
    ):
        """
        Build or refresh the knowledge graph.

        Args:
            repo_path: Path to the repository. If None, uses the repo_path from initialization.
            include_github: Whether to include GitHub data in the graph.
            include_linear: Whether to include Linear data in the graph.
            include_architecture: Whether to extract architecture components.
            use_llm: Whether to use an LLM to enhance the graph.
            llm_provider: The LLM provider to use.
            llm_model: The LLM model to use.
            llm_enhancement_level: The level of LLM enhancement to apply.
            verbose: Whether to print verbose output during the build process.

        Returns:
            A dictionary containing information about the build process.
        """

    def get_architecture_components(
        self,
        component_type: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get architecture components from the knowledge graph.

        Args:
            component_type: Filter by component type (system, service, component, interface)
            parent_id: Filter by parent component ID

        Returns:
            List of architecture components
        """

    def get_entity_history(
        self,
        entity_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_related: bool = False,
        cache: bool = True
    ) -> List[HistoryEntry]:
        """
        Get the history of an entity over time.

        Args:
            entity_id: ID of the entity to get history for
            start_date: Optional start date for the history (ISO format)
            end_date: Optional end date for the history (ISO format)
            include_related: Whether to include related entities
            cache: Whether to use the cache

        Returns:
            List of HistoryEntry objects
        """

    def export_graph(
        self,
        pr_sha: str,
        output_path: str,
        compress: bool = True,
        sign: bool = False,
        key_id: Optional[str] = None,
        base_branch: str = "main",
        max_hops: int = 3,
        enhance_for_llm: bool = True,
        include_causal: bool = True
    ) -> Path:
        """
        Export a relevant slice of the knowledge graph for a PR.

        This method exports a subset of the knowledge graph focused on the files
        modified in a specific PR, along with related nodes and edges. The export
        is saved as a JSON file that can be used by the GitHub App for PR reviews.

        Args:
            pr_sha: SHA of the PR head commit.
            output_path: Path to save the export file.
            compress: Whether to compress the output file.
            sign: Whether to sign the output file with GPG.
            key_id: GPG key ID to use for signing.
            base_branch: Base branch to compare against.
            max_hops: Maximum number of hops to traverse in the graph.
            enhance_for_llm: Whether to enhance the export data for LLM reasoning.
            include_causal: Whether to include causal relationships in the export.

        Returns:
            Path to the exported file.
        """
```

## Return Types

### QueryResult

```python
class QueryResult(BaseModel):
    """Result of a natural language query to the knowledge graph."""

    query: str
    answer: str
    confidence: float = 0.0
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    query_understanding: Optional[str] = None
    reasoning: Optional[str] = None
    execution_time: float = 0.0
```

### DecisionTrailEntry

```python
class DecisionTrailEntry(BaseModel):
    """Entry in a decision trail."""

    id: str
    type: str
    title: str
    rationale: Optional[str] = None
    importance: Optional[float] = None
    trail_position: Optional[int] = None
    timestamp: Optional[datetime] = None
    related_entities: Optional[List["RelatedEntity"]] = None
```

### RelatedEntity

```python
class RelatedEntity(BaseModel):
    """Entity related to another entity."""

    id: str
    type: str
    title: str
    relationship: str
    direction: str
    properties: Optional[Dict[str, Any]] = None
```

### EntityDetails

```python
class EntityDetails(BaseModel):
    """Detailed information about an entity."""

    id: str
    type: str
    title: str
    body: Optional[str] = None
    timestamp: Optional[datetime] = None
    properties: Optional[Dict[str, Any]] = None
    related_entities: Optional[List[RelatedEntity]] = None
```

### ImpactResult

```python
class ImpactResult(EntityDetails):
    """Result of an impact analysis."""

    impact_type: str
    impact_score: float
    impact_path: List[str] = Field(default_factory=list)
```

### HistoryEntry

```python
class HistoryEntry(BaseModel):
    """Entry in an entity's history."""

    id: str
    type: str
    title: str
    timestamp: datetime
    change_type: str
    previous_version: Optional[str] = None
    related_entities: Optional[List[RelatedEntity]] = None
```

### ExportResult

```python
class ExportResult(BaseModel):
    """Result of exporting the knowledge graph."""

    output_path: str
    entity_count: int
    relationship_count: int
    format: str
    compressed: bool
    signed: bool
    signature_path: Optional[str] = None
    execution_time: Optional[float] = None
```

## Framework Adapters

### FrameworkAdapter Protocol

```python
class FrameworkAdapter(Protocol):
    """Protocol defining the interface for framework adapters."""

    def get_name(self) -> str:
        """Return a unique name for this adapter."""
        ...

    def get_version(self) -> str:
        """Return the version of this adapter."""
        ...

    def get_framework_name(self) -> str:
        """Return the name of the framework this adapter supports."""
        ...

    def get_framework_version(self) -> str:
        """Return the version of the framework this adapter supports."""
        ...

    def adapt_functions(self, functions: List[Callable]) -> List[Any]:
        """Adapt Arc Memory functions to framework-specific tools."""
        ...

    def create_agent(self, **kwargs) -> Any:
        """Create an agent using the framework."""
        ...
```

### Adapter Registry Functions

```python
def get_adapter(name: str) -> FrameworkAdapter:
    """
    Get an adapter by name.

    Args:
        name: Name of the adapter to get

    Returns:
        FrameworkAdapter instance

    Raises:
        AdapterNotFoundError: If no adapter with the given name is registered
    """

def register_adapter(adapter: FrameworkAdapter) -> None:
    """
    Register a framework adapter.

    Args:
        adapter: FrameworkAdapter instance to register

    Raises:
        AdapterAlreadyRegisteredError: If an adapter with the same name is already registered
    """

def get_all_adapters() -> Dict[str, FrameworkAdapter]:
    """
    Get all registered adapters.

    Returns:
        Dictionary mapping adapter names to FrameworkAdapter instances
    """

def get_adapter_names() -> List[str]:
    """
    Get the names of all registered adapters.

    Returns:
        List of adapter names
    """

def discover_adapters() -> List[FrameworkAdapter]:
    """
    Discover and register all available adapters.

    Returns:
        List of discovered FrameworkAdapter instances
    """
```

## Caching Behavior

Arc Memory SDK includes a caching system to improve performance for repeated queries. Most methods that query the knowledge graph accept a `cache` parameter that controls whether results are cached and retrieved from cache.

### How Caching Works

1. When a method is called with `cache=True` (the default):
   - The SDK first checks if an identical query exists in the cache
   - If found, it returns the cached result without executing the query again
   - If not found, it executes the query, stores the result in cache, and returns it

2. When a method is called with `cache=False`:
   - The SDK always executes the query, ignoring any cached results
   - The result is not stored in the cache

### Cache Keys

Cache keys are generated based on:
- The method name
- All parameter values
- The repository path

This ensures that cache hits only occur for truly identical queries.

### Cache Invalidation

The cache is automatically invalidated when:
- The knowledge graph is modified (e.g., after running `arc build`)
- The cache TTL (time-to-live) expires (default: 24 hours)

### Cache Location

Cache files are stored in the `.arc/cache` directory within your repository.

### Example: Controlling Cache Behavior

```python
from arc_memory import Arc

arc = Arc(repo_path="./")

# Use cache (default behavior)
result1 = arc.query("Why was the authentication system refactored?")

# Force fresh query, ignore cache
result2 = arc.query("Why was the authentication system refactored?", cache=False)

# Different parameters create different cache entries
result3 = arc.query("Why was the authentication system refactored?", max_results=10)
```

## Error Handling

Arc Memory SDK provides a comprehensive error hierarchy to help you handle errors gracefully in your applications.

### Error Types

```python
class ArcError(Exception):
    """Base class for all Arc Memory errors."""

class DatabaseError(ArcError):
    """Error related to database operations."""

class SDKError(ArcError):
    """Base class for SDK-specific errors."""

class AdapterError(SDKError):
    """Error related to database adapters."""

class QueryError(SDKError):
    """Error related to querying the knowledge graph."""

class BuildError(SDKError):
    """Error related to building the knowledge graph."""

class FrameworkError(SDKError):
    """Error related to framework adapters."""


class ExportError(SDKError):
    """Error related to exporting the knowledge graph."""


class AdapterNotFoundError(FrameworkError):
    """Error raised when an adapter is not found."""

class AdapterAlreadyRegisteredError(FrameworkError):
    """Error raised when an adapter is already registered."""
```

### Error Handling Examples

#### Basic Error Handling

```python
from arc_memory import Arc
from arc_memory.sdk.errors import QueryError, AdapterError, SDKError

try:
    arc = Arc(repo_path="./")
    result = arc.query("Why was the authentication system refactored?")
    print(result.answer)
except QueryError as e:
    print(f"Query failed: {e}")
except AdapterError as e:
    print(f"Database adapter error: {e}")
except SDKError as e:
    print(f"SDK error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

#### Framework Adapter Error Handling

```python
from arc_memory import Arc
from arc_memory.sdk.errors import FrameworkError, AdapterNotFoundError

try:
    arc = Arc(repo_path="./")
    adapter = arc.get_adapter("langchain")
    tools = adapter.adapt_functions([arc.query, arc.get_decision_trail])
except AdapterNotFoundError as e:
    print(f"Adapter not found: {e}")
    print("Available adapters:", arc.get_adapter_names())
except FrameworkError as e:
    print(f"Framework error: {e}")
```

#### Export Error Handling

```python
from arc_memory import Arc
from arc_memory.sdk.errors import ExportSDKError
from pathlib import Path

try:
    arc = Arc(repo_path="./")
    export_path = arc.export_graph(
        pr_sha="abc123",
        output_path="export.json",
        compress=True
    )
    print(f"Export successful: {export_path}")
except ExportSDKError as e:
    print(f"Export failed: {e}")
    # Try again with different parameters
    try:
        export_path = arc.export_graph(
            pr_sha="abc123",
            output_path="export.json",
            compress=False
        )
        print(f"Export successful with fallback: {export_path}")
    except ExportSDKError as e:
        print(f"Export failed again: {e}")
```
