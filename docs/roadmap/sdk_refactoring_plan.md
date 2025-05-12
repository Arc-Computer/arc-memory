# Arc Memory SDK Refactoring Plan

## Business Context

Arc Memory occupies a unique position in the AI memory and knowledge graph landscape:

### Competitive Landscape
- **Horizontal Memory Solutions** (Letta, Mem0, Zep): Offer general-purpose memory for AI agents across domains, focusing on conversation context and personalization.
- **Knowledge Graph Platforms** (WhyHow): Provide semantic structure for RAG pipelines with a focus on determinism and accuracy.
- **Code Context Tools** (Unblocked): Surface contextual information about code to improve developer productivity.

### Arc Memory's Differentiation
- **Vertical Data Model**: Unlike horizontal players, Arc stores causal edges (decision > implication > code-change) gathered directly from GitHub, Linear, Notion, etc.
- **Core Workflow Integration**: Surfaces memory in the diff where engineers live, improving the code review process rather than requiring teams to adopt a separate memory API.
- **High-Stakes ICP**: Focused on Fintech, blockchain, and payment-rail providers who place the highest value on mitigating downtime and incident-response overhead (~$15k/min downtime cost).
- **RL Environment Foundation**: Treats the repository as an RL environment, predicting blast-radius before merge and enabling parallel agent workflows.

### Strategic Direction
The scalability of Arc Memory depends on how quickly we can ship the RL environment loop that enables us to move beyond "deep research for codebases" to a real-time knowledge graph of code for parallel workflows based on active changes and decisions. This SDK refactoring is a critical step in that direction.

### Go-to-Market Developer Experience

For Arc Memory to succeed, we need to make it exceptionally easy for developers to integrate and derive value quickly. Here's how our approach compares to competitors:

#### Quick Start Experience
- **Competitors' Approaches**:
  - **Letta/Mem0/Zep**: Require setting up memory stores, configuring persistence, and managing context windows.
  - **WhyHow**: Requires knowledge graph expertise and schema definition.
  - **Unblocked**: Offers quick IDE plugin installation but limited to passive context retrieval.

- **Arc Memory's Approach**:
  1. **Zero-Config Graph Building**: `pip install arc-memory && arc build` automatically builds a knowledge graph from Git history, GitHub issues/PRs, and other connected sources.
  2. **Instant Agent Integration**: `from arc_memory import ArcAgent; agent = ArcAgent(repo_path="./")` creates an agent with full knowledge of the codebase.
  3. **Framework Adapters**: Pre-built adapters for popular agent frameworks (LangChain, LlamaIndex, etc.) enable one-line integration.
  4. **Progressive Value**: Immediate value from basic queries, with increasing returns as the graph builds over time.

#### Time-to-Value
- **Arc Memory**: Delivers value in three stages:
  1. **Immediate** (minutes): Basic code context and relationship queries
  2. **Short-term** (hours): Temporal analysis and reasoning about code evolution
  3. **Long-term** (days): Predictive insights about change impacts and blast radius

This approach ensures developers can start using Arc Memory with minimal friction while still benefiting from its advanced capabilities as they invest more time.

## Overview

This document outlines a strategic plan to refactor Arc Memory's architecture to prioritize agent integration while maintaining CLI functionality for human users. The goal is to transform Arc Memory into a powerful tool that can be seamlessly integrated into agent workflows while preserving the user experience for direct human interaction.

## Current Architecture Assessment

### Strengths
- Strong CLI interface with intuitive commands
- Robust knowledge graph foundation
- Bi-temporal data model
- Plugin architecture for data sources

### Limitations
- SDK functionality is secondary to CLI
- Agent integration requires subprocess spawning
- Return formats optimized for human readability, not machine consumption
- Limited programmatic composability

## Target Architecture

Drawing inspiration from NVIDIA's Agent Intelligence Toolkit (AIQ) framework-agnostic approach and Neo4j's GraphRAG approach, we'll adopt a plugin-based architecture that treats all components as function calls, enabling true framework agnosticism and database flexibility:

```bash
┌─────────────────────────────────────────────────────────────┐
│                     Agent Frameworks                        │
│  (LangChain, LlamaIndex, AutoGen, CrewAI, Function Calling) │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Arc Memory Plugin System                   │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Framework   │  │ LLM         │  │ Tool                │  │
│  │ Adapters    │  │ Adapters    │  │ Adapters            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Arc Memory Core Functions                  │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Query API   │  │ Context API │  │ Temporal Analysis   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Graph Build │  │ Auto-Refresh│  │ Relationship API    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Code Explain│  │ Reasoning   │  │ Semantic Search     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Arc Memory Core SDK                        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Database    │  │ Ingestors   │  │ Schema              │  │
│  │ Adapters    │  │             │  │                     │  │
│  │ (SQLite/    │  │             │  │                     │  │
│  │  Neo4j)     │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ LLM Client  │  │ Auth        │  │ Utils               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                        ▲
                        │
┌───────────────────────┴─────────────────────────────────────┐
│                  Arc Memory CLI                             │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Commands    │  │ Formatting  │  │ Interactive Mode    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Database Abstraction Layer

A key enhancement to our architecture is the addition of a database abstraction layer that supports both SQLite (for local usage) and Neo4j (for cloud):

```bash
┌─────────────────────────────────────────────────────────────┐
│                  Database Abstraction Layer                 │
│                                                             │
│  ┌─────────────────────────┐      ┌─────────────────────┐   │
│  │                         │      │                     │   │
│  │  SQLite Adapter         │      │  Neo4j Adapter      │   │
│  │  (Local-First)          │      │  (Cloud)            │   │
│  │                         │      │                     │   │
│  └─────────────┬───────────┘      └─────────┬───────────┘   │
│                │                            │               │
│                ▼                            ▼               │
│  ┌─────────────────────────┐      ┌─────────────────────┐   │
│  │                         │      │                     │   │
│  │  SQLite                 │      │  Neo4j GraphRAG     │   │
│  │  Knowledge Graph        │      │  Knowledge Graph    │   │
│  │                         │      │                     │   │
│  └─────────────────────────┘      └─────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

This approach allows us to leverage Neo4j's GraphRAG capabilities in our cloud offering while maintaining our local-first SQLite implementation for individual developers.

## Refactoring Phases

### Phase 1: Minimal SDK API (0.5 months)

1. **Extract Core Logic from Key CLI Commands**
   - Focus on the most essential commands first (`why`, `relate`, `build`)
   - Move business logic from CLI layer to SDK layer
   - Ensure SDK functions return structured data objects
   - Keep the implementation simple and focused on SQLite

2. **Define Basic Return Types**
   - Create simple dataclasses for core return types
   - Support serialization to/from JSON
   - Focus on the most commonly used data structures

3. **Implement Basic Error Handling**
   - Define a simple exception hierarchy
   - Add context information to exceptions
   - Focus on user-friendly error messages

4. **Create Simple Documentation**
   - Document the core SDK functions
   - Provide basic usage examples
   - Focus on getting developers started quickly

### Phase 2: Framework Adapters and LangChain Integration (1 month)

1. **Leverage Existing Plugin Architecture**
   - Use the current `IngestorPlugin` and `IngestorRegistry` as a model
   - Build on our existing plugin system to create a framework-agnostic approach
   - Extend with framework adapter plugins that follow the same pattern

2. **Create Framework Adapter Architecture**
   - Implement a framework adapter protocol and registry
   - Create a discovery mechanism for framework adapters
   - Add helper methods for working with adapters

3. **Implement LangChain Adapter**
   - Create a LangChain adapter following our framework-agnostic approach
   - Convert core SDK functions to LangChain tools
   - Create simple examples of LangChain integration
     ```python
     # Example usage
     from arc_memory.plugins.frameworks import langchain
     tools = langchain.get_tools()
     agent = langchain.create_agent(tools=tools)
     ```

4. **Implement OpenAI Function Calling Adapter**
   - Create an OpenAI adapter following our framework-agnostic approach
   - Convert core SDK functions to OpenAI function definitions
   - Create examples of OpenAI integration

5. **Test with Real-World Scenarios**
   - Create example notebooks with common use cases
   - Test with Protocol Labs repositories
   - Gather feedback and refine the integration

### Phase 3: CLI Updates and Documentation (0.5 months)

1. **Update CLI to Use SDK**
   - Refactor key CLI commands to use the new SDK
   - Ensure backward compatibility for command syntax
   - Focus on maintaining a consistent user experience

2. **Enhance Documentation**
   - Create comprehensive SDK documentation
   - Write usage guides for common scenarios
   - Develop examples for LangChain integration

### Future Phases (Deferred)

1. **Additional Framework Adapters**
   - OpenAI function calling adapter
   - LlamaIndex adapter
   - Other frameworks as needed

2. **Database Abstraction Layer**
   - Create interfaces that work with both SQLite and Neo4j
   - Implement SQLite adapter first with clean interfaces
   - Add Neo4j adapter when cloud offering is developed

3. **Advanced Features**
   - Async support
   - Streaming responses
   - Advanced plugin architecture
   - Interactive mode improvements

## Implementation Guidelines

### SDK Design Principles

1. **Agent-First Design**
   - Optimize function signatures for agent usage
   - Provide context-rich responses
   - Support natural language interfaces

2. **Composability**
   - Design functions that can be easily chained
   - Avoid global state where possible
   - Use consistent parameter naming

3. **Progressive Disclosure**
   - Provide simple interfaces for common tasks
   - Allow access to advanced functionality when needed
   - Use sensible defaults with override options

4. **Performance Awareness**
   - Optimize for low latency in agent scenarios
   - Support batching for efficiency
   - Implement caching where appropriate

### Extending the Existing Plugin Architecture

Arc Memory already has a robust plugin architecture for data ingestion. We'll build upon this foundation to create a comprehensive framework-agnostic system:

1. **Unified Plugin Discovery**
   - Leverage the existing entry points-based discovery mechanism (`arc_memory.plugins`)
   - Extend with additional namespaces for new plugin types:
     ```python
     # pyproject.toml
     [project.entry-points."arc_memory.plugins.ingestors"]
     custom-source = "my_package.my_module:CustomIngestor"

     [project.entry-points."arc_memory.plugins.frameworks"]
     langchain = "my_package.adapters:LangChainAdapter"
     ```
   - Maintain backward compatibility with existing plugins

2. **Expanded Plugin Protocols**
   - Keep the existing `IngestorPlugin` protocol for data sources
   - Add new protocols for different plugin types:
     ```python
     class FrameworkAdapterPlugin(Protocol):
         def get_name(self) -> str: ...
         def get_supported_versions(self) -> List[str]: ...
         def adapt_functions(self, functions: List[Callable]) -> Any: ...
     ```
   - Support both class-based and function-based plugin implementations

3. **Comprehensive Plugin Types**
   - **Ingestor Plugins** (existing): Ingest data from various sources
   - **Framework Adapter Plugins** (new): Connect to agent frameworks
   - **LLM Adapter Plugins** (new): Integrate with LLM providers
   - **Tool Adapter Plugins** (new): Convert functions to tool formats
   - **Memory Adapter Plugins** (new): Integrate with memory systems
   - **Database Adapter Plugins** (new): Support different database backends
     - SQLite Adapter: For local-first usage
     - Neo4j Adapter: For cloud offering, leveraging GraphRAG capabilities

4. **Function-First Design**
   - Treat all components (agents, tools, workflows) as simple function calls
   - Enable true composability: build once, reuse anywhere
   - Allow mixing and matching components from different frameworks

### Developer Onboarding Experience

To ensure rapid adoption, we'll create a frictionless onboarding experience:

1. **One-Line Installation**
   ```bash
   pip install arc-memory
   ```

2. **Quick Start Templates**
   - GitHub repository with ready-to-use examples for common frameworks
   - Copy-paste snippets for immediate integration

3. **Framework-Specific Starter Kits**
   - LangChain: `from arc_memory.plugins import langchain; tools = langchain.get_tools()`
   - LlamaIndex: `from arc_memory.plugins import llamaindex; retriever = llamaindex.get_retriever()`
   - Function Calling: `from arc_memory.plugins import openai; tools = openai.get_tools()`
   - Framework-agnostic: `from arc_memory import ArcMemory; memory = ArcMemory(repo_path="./")`

4. **Interactive Tutorials**
   - Jupyter notebooks with step-by-step guides
   - VS Code Dev Containers with pre-configured environments

5. **CI/CD Integration Examples**
   - GitHub Actions workflow templates
   - GitLab CI pipeline examples
   - Jenkins job configurations

### Testing Strategy

1. **Unit Testing**
   - Achieve high coverage of SDK functions
   - Test edge cases and error conditions
   - Use parameterized tests for variations

2. **Integration Testing**
   - Test with actual agent frameworks
   - Verify end-to-end workflows
   - Include performance benchmarks

3. **Agent Simulation Testing**
   - Create simulated agent interactions
   - Test complex multi-step workflows
   - Verify context preservation

## Key SDK Functions

### Query API
- `query_knowledge_graph(question: str) -> QueryResult`
- `find_entities(query: str, entity_type: Optional[NodeType] = None) -> List[Entity]`
- `get_entity_details(entity_id: str) -> EntityDetails`
- `find_relationships(source_id: str, target_id: Optional[str] = None, relationship_type: Optional[EdgeRel] = None) -> List[Relationship]`
- `search(query: str, filters: Optional[Dict] = None, limit: int = 10) -> List[SearchResult]`

### Graph Building API
- `build_graph(sources: List[DataSource], options: BuildOptions) -> BuildResult`
- `update_graph(since: Optional[datetime] = None) -> UpdateResult`
- `register_data_source(source: DataSource) -> None`
- `get_build_status() -> BuildStatus`
- `schedule_auto_refresh(interval: timedelta) -> None`

### Temporal Analysis API
- `analyze_timeline(entity_id: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> Timeline`
- `find_related_changes(entity_id: str, time_window: timedelta) -> List[Change]`
- `identify_development_phases() -> List[DevelopmentPhase]`
- `compare_entity_at_times(entity_id: str, time1: datetime, time2: datetime) -> EntityComparison`

### Context API
- `get_context_for_file(file_path: str, line_range: Optional[Tuple[int, int]] = None) -> FileContext`
- `get_context_for_function(function_name: str) -> FunctionContext`
- `get_context_for_pr(pr_number: int) -> PRContext`
- `get_context_for_issue(issue_number: int) -> IssueContext`
- `get_context_for_commit(commit_hash: str) -> CommitContext`

### Code Explanation API
- `explain_code(file_path: str, line_range: Optional[Tuple[int, int]] = None) -> CodeExplanation`
- `explain_function(function_name: str) -> FunctionExplanation`
- `explain_change(commit_hash: str, file_path: Optional[str] = None) -> ChangeExplanation`
- `explain_pr(pr_number: int) -> PRExplanation`

### Reasoning API
- `trace_reasoning(entity_id: str, question: str) -> ReasoningTrace`
- `explain_relationship(source_id: str, target_id: str) -> RelationshipExplanation`
- `identify_patterns(entity_ids: List[str]) -> List[Pattern]`
- `generate_insights(entity_id: str) -> List[Insight]`

### Semantic Search API
- `semantic_search(query: str, limit: int = 10) -> List[SearchResult]`
- `find_similar_code(code_snippet: str, limit: int = 10) -> List[CodeSearchResult]`
- `find_similar_entities(entity_id: str, limit: int = 10) -> List[SimilarEntity]`
- `search_by_concept(concept: str, limit: int = 10) -> List[ConceptSearchResult]`

## Migration Path

1. **Gradual Transition**
   - Implement SDK functions alongside existing CLI
   - Add deprecation warnings for direct CLI usage patterns
   - Provide migration examples

2. **Version Strategy**
   - Release SDK as v0.4.0 (alpha)
   - Reach feature parity at v0.5.0 (beta)
   - Stabilize API at v1.0.0

3. **Backward Compatibility**
   - Maintain CLI functionality
   - Support existing scripts and workflows
   - Provide compatibility layers where needed

## Success Metrics

1. **Agent Integration**
   - Number of supported agent frameworks
   - Ease of integration (measured by lines of code)
   - Query latency in agent contexts

2. **Developer Experience**
   - SDK documentation completeness
   - Example coverage for common scenarios
   - Community feedback and adoption
   - Time-to-first-value (target: <5 minutes)

3. **Performance**
   - Query response time
   - Memory usage
   - Throughput for batch operations

4. **Adoption Metrics**
   - Number of repositories using Arc Memory
   - Percentage of users integrating with agents vs. CLI-only
   - Retention rate after initial setup
   - Frequency of API calls per repository

5. **Competitive Positioning**
   - Feature parity with competitors on core functionality
   - Unique value metrics (e.g., accuracy of blast radius prediction)
   - Time-to-value compared to competitors

## Implementation Plan

Building on our existing database abstraction layer (PR #53), we'll implement the SDK refactoring through the following 7 PRs:

### PR 1: Core SDK Structure and Return Types
- Create the basic SDK structure with the `ArcMemory` class
- Define data models for return types
- Implement the framework adapter protocol and registry
- Implement exception hierarchy for error handling

### PR 2: Extract Core Command Logic
- Extract logic from CLI commands into SDK methods
- Implement core API functions (Query API, Context API, etc.)
- Ensure backward compatibility
- Add comprehensive tests

### PR 3: Framework Adapter Architecture
- Implement the framework adapter discovery mechanism
- Create the base adapter protocol
- Add helper methods for working with adapters
- Implement plugin discovery for framework adapters

### PR 4: LangChain Adapter
- Implement the LangChain adapter
- Create examples showing LangChain integration
- Add tests for LangChain integration
- Implement LangChain-specific helper functions

### PR 5: OpenAI Function Calling Adapter
- Implement the OpenAI adapter
- Create examples showing OpenAI integration
- Add tests for OpenAI integration

### PR 6: CLI Updates
- Update CLI commands to use the SDK
- Ensure backward compatibility
- Add deprecation warnings for direct usage patterns
- Optimize CLI performance

### PR 7: Documentation and Examples
- Create comprehensive documentation
- Add examples for each supported framework
- Create tutorials for extending with new frameworks
- Add migration guides for existing users
- Create demo for enterprise customers (e.g., Snowflake)

This implementation plan aligns with our three-phase approach:

- **Phase 1 (0.5 months)**: PRs 1-2 establish the minimal SDK API
- **Phase 2 (1 month)**: PRs 3-5 implement framework adapters, focusing on LangChain integration
- **Phase 3 (0.5 months)**: PRs 6-7 update the CLI and create comprehensive documentation

## Next Steps

1. Begin PR 1 by creating the core SDK structure and return types
2. Extract core logic from the `why`, `relate`, and `build` commands in PR 2
3. Implement the framework adapter architecture in PR 3
4. Create the LangChain adapter in PR 4
5. Implement the OpenAI adapter in PR 5
6. Update the CLI to use the SDK in PR 6
7. Create comprehensive documentation and examples in PR 7
8. Test with Protocol Labs repositories to gather feedback throughout the process

## Implementation Example Building on Existing Plugin Architecture

Here's a simplified example of how we can extend the existing plugin architecture to support framework adapters:

```python
# Existing IngestorPlugin protocol (already implemented)
class IngestorPlugin(Protocol):
    def get_name(self) -> str: ...
    def get_node_types(self) -> List[str]: ...
    def get_edge_types(self) -> List[str]: ...
    def ingest(self, last_processed: Optional[Dict[str, Any]] = None) -> tuple[List[Node], List[Edge], Dict[str, Any]]: ...

# New FrameworkAdapterPlugin protocol
class FrameworkAdapterPlugin(Protocol):
    def get_name(self) -> str: ...
    def get_supported_versions(self) -> List[str]: ...
    def adapt_functions(self, functions: List[Callable]) -> Any: ...

# Generalized PluginRegistry that extends the existing IngestorRegistry pattern
class PluginRegistry:
    def __init__(self):
        self.ingestors = {}  # Existing ingestor plugins
        self.framework_adapters = {}  # New framework adapter plugins
        # Other plugin types...

    def register_ingestor(self, ingestor: IngestorPlugin) -> None:
        self.ingestors[ingestor.get_name()] = ingestor

    def register_framework_adapter(self, adapter: FrameworkAdapterPlugin) -> None:
        self.framework_adapters[adapter.get_name()] = adapter

    # Other registration methods...

# Enhanced discover_plugins function that builds on the existing one
def discover_plugins() -> PluginRegistry:
    registry = PluginRegistry()

    # Register built-in ingestors (existing functionality)
    registry.register_ingestor(GitIngestor())
    registry.register_ingestor(GitHubIngestor())
    registry.register_ingestor(ADRIngestor())

    # Register built-in framework adapters (new functionality)
    registry.register_framework_adapter(LangChainAdapter())
    registry.register_framework_adapter(LlamaIndexAdapter())

    # Discover and register third-party plugins from entry points
    for entry_point in pkg_resources.iter_entry_points("arc_memory.plugins.ingestors"):
        try:
            plugin_class = entry_point.load()
            registry.register_ingestor(plugin_class())
        except Exception as e:
            logger.warning(f"Failed to load ingestor plugin {entry_point.name}: {e}")

    for entry_point in pkg_resources.iter_entry_points("arc_memory.plugins.frameworks"):
        try:
            plugin_class = entry_point.load()
            registry.register_framework_adapter(plugin_class())
        except Exception as e:
            logger.warning(f"Failed to load framework adapter plugin {entry_point.name}: {e}")

    return registry

# LangChain adapter implementation following the existing plugin pattern
class LangChainAdapter:
    def get_name(self) -> str:
        return "langchain"

    def get_supported_versions(self) -> List[str]:
        return ["0.1.0", "0.2.0"]

    def adapt_functions(self, functions: List[Callable]) -> Any:
        from langchain.agents import Tool

        tools = []
        for func in functions:
            tools.append(Tool(
                name=func.__name__,
                func=func,
                description=func.__doc__
            ))

        return tools

# Usage in LangChain
from arc_memory.plugins.frameworks import langchain
tools = langchain.get_tools()
agent = langchain.create_agent(tools=tools)

# Usage without framework
from arc_memory import ArcMemory
memory = ArcMemory(repo_path="./")
result = memory.query_knowledge_graph("What was the reasoning behind the auth refactor?")
```

This approach builds upon the existing plugin architecture while extending it to support framework adapters and other plugin types, maintaining backward compatibility with existing plugins.

## Neo4j Integration Strategy

To ensure a smooth transition from local SQLite to cloud Neo4j, we'll implement the following:

### 1. Database Adapter Implementation

```python
# Database adapter protocol
class DatabaseAdapter(Protocol):
    def get_name(self) -> str: ...
    def get_supported_versions(self) -> List[str]: ...
    def connect(self, connection_params: Dict[str, Any]) -> None: ...
    def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any: ...
    def begin_transaction(self) -> Any: ...
    def commit_transaction(self, transaction: Any) -> None: ...
    def rollback_transaction(self, transaction: Any) -> None: ...

# SQLite adapter implementation
class SQLiteAdapter:
    def get_name(self) -> str:
        return "sqlite"

    def get_supported_versions(self) -> List[str]:
        return ["3.0.0", "3.1.0"]

    # Implementation of other methods...

# Neo4j adapter implementation
class Neo4jAdapter:
    def get_name(self) -> str:
        return "neo4j"

    def get_supported_versions(self) -> List[str]:
        return ["5.0.0", "5.1.0"]

    # Implementation leveraging Neo4j GraphRAG Python Package...
```

### 2. GraphRAG Integration

We'll align our API design with Neo4j's GraphRAG Python Package to ensure compatibility:

1. **Knowledge Graph Construction**:
   - Adopt similar patterns for entity and relationship extraction
   - Use compatible schema definitions
   - Implement chunking and embedding generation

2. **Vector Search Integration**:
   - Support Neo4j's vector search capabilities
   - Implement compatible embedding models
   - Use similar query patterns for hybrid retrieval

3. **Retrieval Augmentation**:
   - Implement GraphRAG-compatible retrieval methods
   - Support both vector and graph-based retrieval
   - Enable hybrid retrieval strategies

### 3. Migration Path

To ensure a smooth transition for users:

1. **Transparent Database Switching**:
   - Allow switching between SQLite and Neo4j with minimal code changes
   - Provide migration utilities for existing SQLite databases
   - Implement automatic schema mapping

2. **Feature Parity**:
   - Ensure all features work with both backends
   - Optimize performance for each backend
   - Provide backend-specific optimizations when appropriate

3. **Cloud Sync**:
   - Implement selective sync between local SQLite and cloud Neo4j
   - Support bidirectional updates
   - Ensure conflict resolution

By leveraging Neo4j's GraphRAG capabilities while maintaining our local-first approach, we can provide a seamless experience for both individual developers and teams, accelerating our roadmap while preserving our unique value proposition.
