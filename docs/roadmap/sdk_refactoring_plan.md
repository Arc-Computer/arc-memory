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

## Framework-Agnostic Design Philosophy

Our SDK refactoring is explicitly designed to follow the framework-agnostic approach pioneered by NVIDIA's Agent Intelligence Toolkit (AIQ). This philosophy has several key principles:

1. **Functions as the Universal Interface**
   - Treat all components (agents, tools, workflows) as simple function calls
   - Provide a consistent interface regardless of the underlying framework
   - Enable easy composition of different components

2. **Building on Existing Plugin Architecture**
   - Leverage and extend our existing plugin system documented in `docs/api/plugins.md`
   - Apply the same patterns that work for our `IngestorPlugin` to framework adapters
   - Use entry points for discoverable, extensible components

3. **True Framework Neutrality**
   - Support multiple agent frameworks without favoring any particular one
   - Allow developers to use Arc Memory with their framework of choice
   - Provide adapters for popular frameworks (LangChain, OpenAI, etc.) while maintaining a core that's framework-independent

4. **Composition and Reuse**
   - Design components that can be easily combined
   - Support mixing tools from different frameworks
   - Enable progressive enhancement of agent capabilities

By following this approach, we ensure that Arc Memory can be used with any agent framework, current or future, without requiring users to replatform or rewrite their code. This maximizes the utility and longevity of our SDK in a rapidly evolving AI ecosystem.

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

### Progressive Disclosure Strategy

The "progressive disclosure" principle is a key aspect of our SDK design that requires detailed planning and implementation. This approach ensures that developers can start using the SDK quickly and expand their usage as their needs grow.

#### Multiple API Layers

1. **Basic API Layer**
   - Simple function signatures with minimal required parameters
   - Sensible defaults for all optional parameters
   - Focus on the most common use cases
   ```python
   # Basic API example
   def query_knowledge_graph(question: str) -> QueryResult:
       """Query the knowledge graph with a natural language question."""
       # Implementation with sensible defaults
   ```

2. **Advanced API Layer**
   - Extended function signatures with additional parameters
   - Fine-grained control over behavior
   - Support for advanced use cases
   ```python
   # Advanced API example
   def query_knowledge_graph_advanced(
       question: str,
       max_results: int = 5,
       confidence_threshold: float = 0.7,
       search_strategy: str = "semantic",
       context_size: int = 3
   ) -> DetailedQueryResult:
       """Query the knowledge graph with advanced options."""
       # Implementation with customizable behavior
   ```

3. **Expert API Layer**
   - Hooks for customizing behavior with callbacks
   - Access to internal components and states
   - Support for integration with custom workflows
   ```python
   # Expert API example
   def query_knowledge_graph_with_callback(
       question: str,
       pre_process: Optional[Callable] = None,
       post_process: Optional[Callable] = None,
       # other parameters
   ) -> QueryResult:
       """Query the knowledge graph with custom pre/post-processing."""
       # Implementation with extensibility hooks
   ```

#### Implementation Guidelines for Progressive Disclosure

1. **Documentation Stratification**
   - Basic tutorials and quick starts focus on simple APIs
   - Advanced guides detail additional parameters and options
   - Expert documentation covers customization hooks and internal architecture

2. **API Discovery Paths**
   - Design clear paths for developers to discover advanced options
   - Use IDE hints (docstrings, method signatures) to guide discovery
   - Provide examples that progressively introduce more complex features

3. **Method Organization**
   - Group methods logically by functionality
   - Use consistent naming patterns to indicate complexity level
     - Basic: `method_name()`
     - Advanced: `method_name_advanced()` or `method_name_with_options()`
     - Expert: `method_name_with_callback()` or `method_name_custom()`

4. **Testing Strategy**
   - Test basic functionality with default parameters
   - Test advanced options with various combinations
   - Test customization hooks with mock callbacks

### Backward Compatibility Strategy

Maintaining backward compatibility is critical during this refactoring to ensure existing users can continue to use Arc Memory without disruption while transitioning to the SDK at their own pace.

#### CLI Command Preservation

1. **Command Functionality**
   - Preserve all existing CLI command syntax and behavior
   - Ensure output formats remain consistent for scripts that parse CLI output
   - Maintain all current command options and flags

2. **Implementation Approach**
   - Refactor CLI commands to use the new SDK internally
   - Add adapter layers where necessary to transform SDK outputs to CLI-friendly formats
   - Keep all current CLI entry points functional
   ```python
   # Example of CLI command using SDK internally
   @app.command()
   def why(entity: str, format: str = "text"):
       """Find the reasoning behind a code change, decision, or component."""
       # Use SDK internally but preserve CLI output format
       memory = ArcMemory(repo_path="./")
       result = memory.query_knowledge_graph(f"Why {entity}?")

       # Format result for CLI output to maintain backward compatibility
       if format == "text":
           echo_text_format(result)
       elif format == "json":
           echo_json_format(result)
   ```

#### Configuration Compatibility

1. **Configuration Files**
   - Support existing configuration file formats and locations
   - Gracefully handle missing new configuration options
   - Provide migration utilities for updating configuration files

2. **Environment Variables**
   - Maintain support for existing environment variables
   - Add new environment variables with a consistent naming scheme
   - Document compatibility between old and new variables

#### Data Format Compatibility

1. **Database Schema**
   - Ensure backward compatibility with existing SQLite databases
   - Provide automatic migration for database schema changes
   - Support reading from old format and writing to new format

2. **Export/Import Formats**
   - Maintain compatibility with existing export formats
   - Add version indicators to new export formats
   - Provide conversion utilities between format versions

#### Deprecation Strategy

1. **Phased Approach**
   - Phase 1: Introduce SDK while maintaining full backward compatibility
   - Phase 2: Add deprecation warnings for features slated for removal
   - Phase 3: Remove deprecated features in major version updates

2. **Deprecation Warnings**
   - Add clear deprecation warnings with migration paths
   - Provide specific timelines for feature removal
   - Include links to documentation on how to migrate
   ```python
   def deprecated_method(param):
       warnings.warn(
           "deprecated_method is deprecated and will be removed in version 2.0.0. "
           "Use new_method instead. See https://docs.example.com/migration for details.",
           DeprecationWarning,
           stacklevel=2
       )
       # Call new implementation
       return new_method(param)
   ```

3. **Documentation**
   - Clearly mark deprecated features in documentation
   - Provide migration guides for moving from old to new patterns
   - Offer code examples showing both old and new approaches side by side

#### Testing for Backward Compatibility

1. **Regression Testing**
   - Comprehensive test suite for existing CLI functionality
   - Integration tests that verify backward compatibility
   - Automated checks for breaking changes

2. **Compatibility Matrix**
   - Define and test compatibility with previous versions
   - Document supported upgrade paths
   - Verify interoperability between components at different versions

3. **User Acceptance Testing**
   - Test with real-world repositories and workflows
   - Engage existing users in beta testing
   - Prioritize fixing backward compatibility issues

#### Migration Support

1. **Migration Utilities**
   - Provide scripts for migrating from CLI-based workflows to SDK
   - Create tools for updating configuration files and data formats
   - Build linters to identify deprecated usage patterns

2. **Transition Documentation**
   - Create comprehensive migration guides
   - Provide examples of migrating common workflows
   - Document equivalences between old and new approaches

3. **Support Timeline**
   - Clearly communicate support timeline for legacy features
   - Provide long-term support for critical backward compatibility
   - Plan migration windows timed with major releases

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

Building on our existing database abstraction layer (PR #53), we'll implement the SDK refactoring through the following refined PRs:

### PR 1: Core SDK Structure and Database Integration

#### Overview
PR 1 will establish the foundation for the Arc Memory SDK by creating the core `Arc` class, integrating with the existing database adapters, defining return types, and implementing the framework adapter protocol.

#### Key Components

1. **Core `Arc` Class**:
   - Main entry point for SDK users
   - Connection to database layer through adapters
   - Core methods for accessing the knowledge graph

2. **Return Types and Data Models**:
   - Structured return types for SDK functions
   - Serialization/deserialization capability
   - Simple, focused types for essential data

3. **Database Adapter Integration**:
   - Leverage existing database adapters (`sqlite_adapter.py`, `neo4j_adapter.py`)
   - Implement dependency injection for adapters
   - Create factory method for getting appropriate adapter

4. **Framework Adapter Protocol**:
   - Define interface for framework adapters
   - Create adapter registry mechanism
   - Support discovery of adapters via entry points

5. **Error Handling**:
   - Implement exception hierarchy
   - Add context information to exceptions
   - Ensure user-friendly error messages

#### Files to Create/Modify

1. **New Files**:
   - `arc_memory/sdk/__init__.py`: Package initialization
   - `arc_memory/sdk/core.py`: Core `Arc` class implementation
   - `arc_memory/sdk/models.py`: Return type models
   - `arc_memory/sdk/adapters/__init__.py`: Adapter package initialization
   - `arc_memory/sdk/adapters/base.py`: Framework adapter protocol
   - `arc_memory/sdk/adapters/registry.py`: Adapter registry
   - `tests/sdk/test_core.py`: Tests for core functionality
   - `tests/sdk/test_models.py`: Tests for return type models
   - `tests/sdk/test_adapters.py`: Tests for adapter functionality

2. **Files to Modify**:
   - `arc_memory/__init__.py`: Expose `Arc` class
   - `arc_memory/errors.py`: Add SDK-specific exceptions
   - `pyproject.toml`: Add entry points for framework adapters

#### Detailed Implementation Plan

##### 1. Core `Arc` Class Implementation (`arc_memory/sdk/core.py`)

The `Arc` class will be the main entry point for SDK users, providing access to the knowledge graph through a clean, intuitive interface:

```python
class Arc:
    """Main entry point for the Arc Memory SDK.

    This class provides access to the knowledge graph through a clean, intuitive interface.
    It connects to the database layer through adapters and provides core methods for
    accessing the knowledge graph.

    Args:
        repo_path: Path to the repository to analyze.
        adapter_type: Type of database adapter to use. If None, uses the configured adapter.
    """

    def __init__(
        self,
        repo_path: Union[str, Path],
        adapter_type: Optional[str] = None
    ) -> None:
        self.repo_path = Path(repo_path)
        self.adapter = get_adapter(adapter_type)

        # Connect to the database
        self._ensure_connected()

    def _ensure_connected(self) -> None:
        """Ensure the adapter is connected to the database."""
        if not self.adapter.is_connected():
            from arc_memory.sql.db import get_db_path
            db_path = get_db_path()
            self.adapter.connect({"db_path": str(db_path)})
            # Initialize the database schema to ensure tables exist
            self.adapter.init_db()

    # Core methods for accessing the knowledge graph
    def query(self, question: str) -> QueryResult:
        """Query the knowledge graph with a natural language question.

        Args:
            question: The natural language question to ask.

        Returns:
            A QueryResult containing the answer and supporting evidence.
        """
        # Implementation will be added in PR 2a
        pass

    def get_node_by_id(self, node_id: str) -> Optional[EntityDetails]:
        """Get a node by its ID.

        Args:
            node_id: The ID of the node.

        Returns:
            The node details, or None if it doesn't exist.
        """
        self._ensure_connected()
        node = self.adapter.get_node_by_id(node_id)
        if node is None:
            return None

        # Get relationships for this node
        outgoing = self.adapter.get_edges_by_src(node_id)
        incoming = self.adapter.get_edges_by_dst(node_id)

        # Convert to EntityDetails model
        return EntityDetails.from_node_and_edges(node, outgoing, incoming)

    def add_nodes_and_edges(self, nodes: List[Node], edges: List[Edge]) -> None:
        """Add nodes and edges to the knowledge graph.

        Args:
            nodes: The nodes to add.
            edges: The edges to add.
        """
        self._ensure_connected()
        self.adapter.add_nodes_and_edges(nodes, edges)
```

##### 2. Return Type Models (`arc_memory/sdk/models.py`)

Define structured return types for SDK functions:

```python
class QueryResult(BaseModel):
    """Result of a query to the knowledge graph."""

    answer: str
    confidence: float = 1.0
    sources: List[Dict[str, Any]] = Field(default_factory=list)

class EntityDetails(BaseModel):
    """Detailed information about an entity in the knowledge graph."""

    id: str
    type: NodeType
    title: Optional[str] = None
    body: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_node_and_edges(
        cls,
        node: Dict[str, Any],
        outgoing: List[Dict[str, Any]],
        incoming: List[Dict[str, Any]]
    ) -> "EntityDetails":
        """Create an EntityDetails instance from a node and its edges."""
        relationships = []

        for edge in outgoing:
            relationships.append({
                "direction": "outgoing",
                "type": edge["rel"],
                "target_id": edge["dst"],
                "properties": edge.get("properties", {})
            })

        for edge in incoming:
            relationships.append({
                "direction": "incoming",
                "type": edge["rel"],
                "source_id": edge["src"],
                "properties": edge.get("properties", {})
            })

        return cls(
            id=node["id"],
            type=node["type"],
            title=node.get("title"),
            body=node.get("body"),
            properties=node.get("extra", {}),
            relationships=relationships
        )
```

##### 3. Framework Adapter Protocol (`arc_memory/sdk/adapters/base.py`)

Define the interface for framework adapters:

```python
class FrameworkAdapter(Protocol):
    """Protocol defining the interface for framework adapters.

    Framework adapters are responsible for adapting Arc Memory functions to
    specific agent frameworks (LangChain, OpenAI, etc.).
    """

    def get_name(self) -> str:
        """Return a unique name for this adapter.

        Returns:
            A string identifier for this adapter, e.g., "langchain", "openai".
        """
        ...

    def get_supported_versions(self) -> List[str]:
        """Return a list of supported framework versions.

        Returns:
            A list of version strings, e.g., ["0.1.0", "0.2.0"].
        """
        ...

    def adapt_functions(self, functions: List[Callable]) -> Any:
        """Adapt Arc Memory functions to the framework's format.

        Args:
            functions: List of functions to adapt.

        Returns:
            Framework-specific representation of the functions.
        """
        ...
```

##### 4. Adapter Registry (`arc_memory/sdk/adapters/registry.py`)

Create a registry for managing framework adapters:

```python
class FrameworkAdapterRegistry:
    """Registry for framework adapters.

    The registry manages the discovery and registration of adapters, and provides
    methods for retrieving adapters by name.
    """

    def __init__(self):
        """Initialize an empty registry."""
        self.adapters: Dict[str, FrameworkAdapter] = {}

    def register(self, adapter: FrameworkAdapter) -> None:
        """Register an adapter with the registry.

        Args:
            adapter: An instance of a class implementing the FrameworkAdapter protocol.
        """
        name = adapter.get_name()
        self.adapters[name] = adapter

    def get(self, name: str) -> Optional[FrameworkAdapter]:
        """Get an adapter by name.

        Args:
            name: The name of the adapter to retrieve.

        Returns:
            The adapter instance, or None if not found.
        """
        return self.adapters.get(name)

    def list_adapters(self) -> List[str]:
        """List all registered adapters.

        Returns:
            A list of adapter names.
        """
        return list(self.adapters.keys())

    @classmethod
    def discover(cls) -> "FrameworkAdapterRegistry":
        """Discover and register all available adapters.

        Returns:
            A registry containing all discovered adapters.
        """
        registry = cls()

        # Discover adapters from entry points
        for entry_point in pkg_resources.iter_entry_points("arc_memory.plugins.frameworks"):
            try:
                adapter_class = entry_point.load()
                registry.register(adapter_class())
                logger.info(f"Loaded framework adapter: {entry_point.name}")
            except Exception as e:
                logger.warning(f"Failed to load framework adapter {entry_point.name}: {e}")

        return registry
```

##### 5. Error Handling (`arc_memory/errors.py`)

Add SDK-specific exceptions:

```python
class SDKError(ArcError):
    """Base class for SDK-related errors."""
    pass

class AdapterError(SDKError):
    """Error raised when there's an issue with an adapter."""
    pass

class QueryError(SDKError):
    """Error raised when querying the knowledge graph fails."""
    pass

class BuildError(SDKError):
    """Error raised when building the knowledge graph fails."""
    pass
```

##### 6. Testing Strategy

We'll implement comprehensive tests for the SDK components:

```python
# tests/sdk/test_core.py
import pytest
from pathlib import Path

from arc_memory.sdk import Arc
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel

def test_arc_initialization():
    """Test that Arc can be initialized."""
    arc = Arc(repo_path="./")
    assert arc is not None
    assert arc.repo_path == Path("./")
    assert arc.adapter is not None

def test_get_node_by_id(mocker):
    """Test getting a node by ID."""
    # Mock the adapter
    mock_adapter = mocker.MagicMock()
    mock_adapter.is_connected.return_value = True
    mock_adapter.get_node_by_id.return_value = {
        "id": "test-node",
        "type": NodeType.COMMIT,
        "title": "Test Node",
        "body": "Test body",
        "extra": {"key": "value"}
    }
    mock_adapter.get_edges_by_src.return_value = []
    mock_adapter.get_edges_by_dst.return_value = []

    # Create Arc with the mock adapter
    arc = Arc(repo_path="./")
    arc.adapter = mock_adapter

    # Get the node
    node = arc.get_node_by_id("test-node")

    # Verify the result
    assert node is not None
    assert node.id == "test-node"
    assert node.type == NodeType.COMMIT
    assert node.title == "Test Node"
    assert node.body == "Test body"
    assert node.properties == {"key": "value"}
    assert node.relationships == []

def test_add_nodes_and_edges(mocker):
    """Test adding nodes and edges."""
    # Mock the adapter
    mock_adapter = mocker.MagicMock()
    mock_adapter.is_connected.return_value = True

    # Create Arc with the mock adapter
    arc = Arc(repo_path="./")
    arc.adapter = mock_adapter

    # Create test nodes and edges
    nodes = [
        Node(id="node1", type=NodeType.COMMIT, title="Node 1"),
        Node(id="node2", type=NodeType.PR, title="Node 2")
    ]
    edges = [
        Edge(src="node1", dst="node2", rel=EdgeRel.RELATED_TO)
    ]

    # Add nodes and edges
    arc.add_nodes_and_edges(nodes, edges)

    # Verify the adapter was called
    mock_adapter.add_nodes_and_edges.assert_called_once_with(nodes, edges)
```

```python
# tests/sdk/test_models.py
import pytest
from arc_memory.sdk.models import EntityDetails, QueryResult
from arc_memory.schema.models import NodeType

def test_query_result_model():
    """Test the QueryResult model."""
    result = QueryResult(answer="Test answer", confidence=0.8, sources=[{"id": "source1"}])
    assert result.answer == "Test answer"
    assert result.confidence == 0.8
    assert result.sources == [{"id": "source1"}]

    # Test default values
    result = QueryResult(answer="Test answer")
    assert result.answer == "Test answer"
    assert result.confidence == 1.0
    assert result.sources == []

def test_entity_details_from_node_and_edges():
    """Test creating EntityDetails from a node and edges."""
    node = {
        "id": "test-node",
        "type": NodeType.COMMIT,
        "title": "Test Node",
        "body": "Test body",
        "extra": {"key": "value"}
    }
    outgoing = [
        {"src": "test-node", "dst": "target1", "rel": "RELATED_TO", "properties": {"weight": 0.5}}
    ]
    incoming = [
        {"src": "source1", "dst": "test-node", "rel": "DEPENDS_ON", "properties": {}}
    ]

    entity = EntityDetails.from_node_and_edges(node, outgoing, incoming)

    assert entity.id == "test-node"
    assert entity.type == NodeType.COMMIT
    assert entity.title == "Test Node"
    assert entity.body == "Test body"
    assert entity.properties == {"key": "value"}
    assert len(entity.relationships) == 2

    # Check outgoing relationship
    outgoing_rel = [r for r in entity.relationships if r["direction"] == "outgoing"][0]
    assert outgoing_rel["type"] == "RELATED_TO"
    assert outgoing_rel["target_id"] == "target1"
    assert outgoing_rel["properties"] == {"weight": 0.5}

    # Check incoming relationship
    incoming_rel = [r for r in entity.relationships if r["direction"] == "incoming"][0]
    assert incoming_rel["type"] == "DEPENDS_ON"
    assert incoming_rel["source_id"] == "source1"
    assert incoming_rel["properties"] == {}
```

```python
# tests/sdk/test_adapters.py
import pytest
from arc_memory.sdk.adapters.base import FrameworkAdapter
from arc_memory.sdk.adapters.registry import FrameworkAdapterRegistry

class MockAdapter:
    def get_name(self):
        return "mock"

    def get_supported_versions(self):
        return ["1.0.0"]

    def adapt_functions(self, functions):
        return [f.__name__ for f in functions]

def test_adapter_registry():
    """Test the FrameworkAdapterRegistry."""
    registry = FrameworkAdapterRegistry()
    adapter = MockAdapter()

    # Register the adapter
    registry.register(adapter)

    # Get the adapter
    retrieved = registry.get("mock")
    assert retrieved is adapter

    # List adapters
    adapters = registry.list_adapters()
    assert adapters == ["mock"]

    # Try to get a non-existent adapter
    assert registry.get("nonexistent") is None

def test_adapter_discovery(mocker):
    """Test adapter discovery from entry points."""
    # Mock pkg_resources.iter_entry_points
    mock_entry_point = mocker.MagicMock()
    mock_entry_point.name = "mock"
    mock_entry_point.load.return_value = MockAdapter

    mocker.patch(
        "pkg_resources.iter_entry_points",
        return_value=[mock_entry_point]
    )

    # Discover adapters
    registry = FrameworkAdapterRegistry.discover()

    # Check that the adapter was discovered
    assert "mock" in registry.list_adapters()
    adapter = registry.get("mock")
    assert adapter.get_name() == "mock"
    assert adapter.get_supported_versions() == ["1.0.0"]
```

#### Summary and Next Steps

We now have a comprehensive implementation plan for PR 1 that:

1. **Establishes the Core SDK Structure**:
   - Creates the `Arc` class as the main entry point
   - Defines return type models for structured data
   - Implements the framework adapter protocol and registry
   - Integrates with existing database adapters

2. **Follows Best Practices**:
   - Uses a clean, intuitive naming convention
   - Provides a framework-agnostic design
   - Maintains backward compatibility
   - Includes comprehensive tests

3. **Prepares for Future PRs**:
   - Sets up the foundation for extracting CLI commands into SDK methods
   - Creates the adapter architecture for framework integration
   - Establishes patterns for error handling and testing

**Next Steps**:

1. Implement the core `Arc` class and related components
2. Write tests for all components
3. Update documentation with usage examples
4. Prepare for PR 2a, which will extract query-related CLI commands into SDK methods

#### Implementation Approach for PR 1

**Main Class Naming and Structure:**
- Use "Arc" as the main class name for the SDK (instead of "ArcMemory")
- This provides a clean, intuitive import pattern: `from arc_memory import Arc`
- Aligns with competitor approaches (Mem0 uses `Memory`, Graphiti uses `Graphiti`)
- Optimizes for developer experience with minimal integration code
- Structure the code to enable framework-agnostic usage while supporting specific framework adapters

**Implementation Structure:**
- Create a new module `arc_memory/sdk/core.py` with the `Arc` class
- Update `arc_memory/__init__.py` to expose the `Arc` class directly
- Implement the database adapter integration in the `Arc` class
- Create the framework adapter protocol and registry

**Example Usage:**
```python
from arc_memory import Arc

# Initialize Arc with a repository path
arc = Arc(repo_path="./my-repo")

# Query the knowledge graph
result = arc.query("What was the reasoning behind the auth refactor?")

# Get a node by ID
node = arc.get_node_by_id("commit-123")

# Add nodes and edges
arc.add_nodes_and_edges(nodes, edges)
```

**Database Adapter Priority:**
- Implement both SQLite and Neo4j adapters from the start, with Neo4j as a stub implementation
- Establish the adapter interface based on real requirements for both implementations
- Ensure the core SDK works with SQLite immediately
- Lay the groundwork for the cloud strategy without delaying the initial release
- Avoid major refactoring when fully implementing the Neo4j adapter later

**Framework Adapter Scope:**
- Follow the NVIDIA AIQ pattern of treating components as function calls
- Create a clean adapter protocol that any framework can implement
- Ensure core SDK functions work without any framework dependencies
- Start with LangChain as a reference implementation while maintaining framework agnosticism

**Testing Strategy:**
- Write tests alongside implementation to ensure functionality works as expected
- Provide documentation of expected behavior through test cases
- Make it easier to refactor with confidence
- Help identify edge cases early
- Use a combination of unit tests for individual components and integration tests

**Documentation Approach:**
- Start with basic usage examples that can be refined based on user feedback
- Include clear docstrings for all public functions and classes
- Create a few key usage examples demonstrating the most common workflows
- Develop a simple "Getting Started" guide
- Generate API reference documentation from docstrings

### PR 2a: Extract Core Query & Relate Functions

#### Overview
PR 2a will extract logic from query-related CLI commands into SDK methods, focusing on the `why` and `relate` commands. This will provide a clean, agent-friendly API for querying the knowledge graph and exploring entity relationships.

#### Key Components

1. **Enhanced Query API**:
   ```python
   def query(
       self,
       question: str,
       max_results: int = 5,
       max_hops: int = 3,
       include_causal: bool = True,  # Emphasize causal relationships
       cache: bool = True,
       callback: Optional[ProgressCallback] = None
   ) -> QueryResult:
       """Query the knowledge graph using natural language.

       This method enables natural language queries about the codebase, focusing on
       causal relationships and decision trails. It's particularly useful for understanding
       why certain changes were made and their implications.
       """
   ```

2. **Enhanced Entity Relationship API**:
   ```python
   def get_related_entities(
       self,
       entity_id: str,
       relationship_types: Optional[List[str]] = None,
       direction: str = "both",  # "outgoing", "incoming", or "both"
       max_results: int = 10,
       include_properties: bool = True,  # Include edge properties
       cache: bool = True
   ) -> List[EntityDetails]:
       """Get entities related to a specific entity.

       This method enables exploration of relationships between entities in the knowledge graph.
       It's particularly useful for understanding dependencies between components and tracing
       the impact of changes.
       """
   ```

3. **Enhanced Decision Trail API**:
   ```python
   def get_decision_trail(
       self,
       file_path: str,
       line_number: int,
       max_results: int = 5,
       max_hops: int = 3,
       include_rationale: bool = True,  # Extract decision rationale
       cache: bool = True,
       callback: Optional[ProgressCallback] = None
   ) -> List[EntityDetails]:
       """Get the decision trail for a specific line in a file.

       This method traces the history of a specific line in a file, showing the commit
       that last modified it and related entities such as PRs, issues, and ADRs. It's
       particularly useful for understanding why a particular piece of code exists.
       """
   ```

4. **Component Impact API (Blast Radius)**:
   ```python
   def get_component_impact(
       self,
       entity_ids: List[str],
       max_depth: int = 3,
       impact_types: Optional[List[str]] = None,
       cache: bool = True,
       callback: Optional[ProgressCallback] = None
   ) -> Dict[str, List[EntityDetails]]:
       """Get the potential impact of changes to specific entities.

       This method analyzes the knowledge graph to identify components that may be
       affected by changes to the specified entities. It's particularly useful for
       assessing the blast radius of proposed changes.
       """
   ```

5. **Temporal Analysis API**:
   ```python
   def get_entity_history(
       self,
       entity_id: str,
       start_date: Optional[datetime] = None,
       end_date: Optional[datetime] = None,
       include_related: bool = True,
       max_results: int = 20,
       cache: bool = True
   ) -> List[Dict[str, Any]]:
       """Get the history of an entity over time.

       This method retrieves the history of an entity, including changes and related
       events. It's particularly useful for understanding how a component has evolved
       over time.
       """
   ```

6. **Caching Implementation**:
   - Implement a caching mechanism for query results and entity details
   - Support time-based expiration (TTL)
   - Provide cache statistics and invalidation options
   - Optimize for repeated queries from agents

7. **Progress Reporting**:
   - Implement callback-based progress reporting for long-running operations
   - Support both human-readable and machine-readable formats
   - Enable cancellation of operations
   - Include detailed progress metrics

#### Implementation Priorities

1. **Query API** and **Decision Trail API**: These directly address the primary persona's need to understand context and decisions.
2. **Entity Relationship API**: This supports understanding component relationships, which is critical for both primary and secondary personas.
3. **Component Impact API**: This lays groundwork for blast radius prediction, a key differentiator for Arc Memory.
4. **Temporal Analysis API**: This supports understanding system evolution, which is important for all personas but especially the secondary and tertiary ones.

#### Testing Strategy

- Implement comprehensive unit tests for all new API methods
- Create integration tests that verify end-to-end functionality
- Test with both human and agent usage patterns
- Verify caching behavior and performance improvements

### PR 2b: Extract Build & Refresh Functions
- Extract logic from build-related CLI commands into SDK methods (`build`, `refresh`)
- Implement Graph Building API functions
- Ensure backward compatibility for these commands
- Add comprehensive tests for build functionality

### PR 3: Framework Adapter Architecture
- Implement the framework adapter discovery mechanism
- Create the base adapter protocol
- Add helper methods for working with adapters
- Implement plugin discovery for framework adapters
- Add tests for the adapter architecture

### PR 4: Basic Framework Adapters Implementation
- Implement core adapters for both LangChain and OpenAI
- Create foundational patterns for both frameworks
- Implement basic conversion of SDK functions to tool formats
- Add shared testing utilities for adapters

### PR 5: Advanced Adapter Features
- Implement advanced adapter features for LangChain and OpenAI
- Create examples showing integration with both frameworks
- Add comprehensive tests for all adapter functionality
- Implement framework-specific helper functions

### PR 6: Testing Infrastructure
- Create comprehensive testing infrastructure
- Implement test fixtures and mocks for different components
- Add integration tests with actual frameworks
- Implement performance benchmarks and regression tests

### PR 7: CLI Updates and Documentation
- Update CLI commands to use the SDK
- Ensure backward compatibility
- Add deprecation warnings for direct usage patterns
- Create comprehensive documentation and examples
- Add migration guides for existing users
- Create demo for enterprise customers (e.g., Snowflake)

**Backward Compatibility Approach:**
- Design the SDK with a clean, intuitive interface optimized for agent usage
- Implement CLI commands as thin wrappers around the SDK functions
- Maintain backward compatibility for CLI syntax and behavior
- Add deprecation warnings for any CLI features that will change in future versions
- Provide migration guides for users transitioning from CLI to SDK
- This approach serves both technical teams who prefer direct SDK integration and users who are comfortable with the existing CLI workflow

This refined implementation plan addresses key risks and ensures more manageable PR sizes:

- **Better Database Integration**: PR #1 explicitly addresses database abstraction from the start
- **More Manageable PR Sizes**: Splitting core command extraction into PR #2a and #2b
- **Logical Grouping**: Organizing adapters by functionality rather than by framework
- **Testing Emphasis**: Adding a dedicated PR for comprehensive testing

The implementation plan still aligns with our three-phase approach:

- **Phase 1 (0.5 months)**: PRs 1, 2a, and 2b establish the minimal SDK API
- **Phase 2 (1 month)**: PRs 3, 4, 5, and 6 implement the framework adapters and testing
- **Phase 3 (0.5 months)**: PR 7 updates the CLI and creates comprehensive documentation

## Next Steps

1. Begin PR 1 by creating the core SDK structure with database integration
2. Extract query functionality in PR 2a, focusing on `why` and `relate` commands
3. Extract build functionality in PR 2b, focusing on `build` and `refresh` commands
4. Implement the framework adapter architecture in PR 3
5. Create basic adapters for both LangChain and OpenAI in PR 4
6. Add advanced adapter features in PR 5
7. Implement comprehensive testing infrastructure in PR 6
8. Update the CLI and documentation in PR 7
9. Test with Protocol Labs repositories to gather feedback throughout the process

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
