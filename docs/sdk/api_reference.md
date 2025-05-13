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
        cache: bool = True
    ) -> List[ImpactAnalysisResult]:
        """
        Analyze the potential impact of changes to a component.

        Args:
            component_id: ID of the component to analyze
            impact_types: Optional list of impact types to include ("direct", "indirect", "potential")
            max_depth: Maximum depth to traverse in the graph
            cache: Whether to use the cache

        Returns:
            List of ImpactAnalysisResult objects
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
        output_path: str,
        pr_sha: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        format: str = "json",
        compress: bool = False,
        sign: bool = False,
        key_id: Optional[str] = None,
        base_branch: Optional[str] = None,
        max_hops: int = 3,
        optimize_for_llm: bool = False,
        include_causal: bool = True
    ) -> ExportResult:
        """
        Export the knowledge graph to a file.

        Args:
            output_path: Path to save the exported graph
            pr_sha: Optional PR SHA to filter by
            entity_types: Optional list of entity types to include
            start_date: Optional start date for entities (ISO format)
            end_date: Optional end date for entities (ISO format)
            format: Format to export in ("json", "jsonl", "csv", "graphml")
            compress: Whether to compress the output
            sign: Whether to sign the output with GPG
            key_id: GPG key ID to use for signing
            base_branch: Base branch to compare against for PR analysis
            max_hops: Maximum number of hops to include
            optimize_for_llm: Whether to optimize the output for LLMs
            include_causal: Whether to include causal relationships

        Returns:
            ExportResult object
        """
```

## Return Types

### QueryResult

```python
class QueryResult(BaseModel):
    """Result of a query to the knowledge graph."""

    answer: str
    confidence: float
    evidence: List[Dict[str, Any]]
    query_understanding: Optional[str] = None
    reasoning: Optional[str] = None
    execution_time: Optional[float] = None
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

### ImpactAnalysisResult

```python
class ImpactAnalysisResult(BaseModel):
    """Result of an impact analysis."""

    id: str
    type: str
    title: str
    impact_score: float
    impact_type: str
    impact_path: List[str]
    properties: Optional[Dict[str, Any]] = None
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

## Error Types

```python
class ArcError(Exception):
    """Base class for all Arc Memory errors."""

class DatabaseError(ArcError):
    """Error related to database operations."""

class AdapterError(ArcError):
    """Error related to framework adapters."""

class AdapterNotFoundError(AdapterError):
    """Error raised when an adapter is not found."""

class AdapterAlreadyRegisteredError(AdapterError):
    """Error raised when an adapter is already registered."""

class QueryError(ArcError):
    """Error related to querying the knowledge graph."""

class ExportError(ArcError):
    """Error related to exporting the knowledge graph."""
```
