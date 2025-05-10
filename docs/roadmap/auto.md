# Implementation Plan for Auto-Refreshing Knowledge Graph

Based on the existing codebase structure, this document outlines a detailed implementation plan for adding auto-refresh capabilities to Arc Memory, with considerations for both SQLite (local) and Neo4j (cloud) backends.

## 1. Overview

The auto-refresh functionality will enable Arc Memory to proactively update its knowledge graph on a schedule, ensuring users always have access to the most current information without manually running `arc build --incremental`. This will be implemented by creating a dedicated refresh command that can be scheduled using system tools (cron, Task Scheduler, launchd) to periodically check for new data from configured sources (GitHub, Linear, etc.) and trigger incremental updates when changes are detected.

### Neo4j Integration Considerations

While the initial implementation will focus on SQLite for local usage, the design will account for future Neo4j integration in the cloud offering:

- The refresh logic will be database-agnostic, working with both SQLite and Neo4j
- We'll leverage Neo4j's Change Data Capture (CDC) capabilities for the cloud offering
- The metadata structure will be designed to be compatible with both backends
- We'll adopt patterns from Neo4j's GraphRAG Python Package and LLM Graph Builder for processing new content

## 2. Key Components

### A. Auto-Refresh Module (`arc_memory/auto_refresh.py`)

This will be the core module responsible for managing the refresh process:

- Implement core refresh functionality that can be called from the CLI
- Track per-repository update timestamps in the existing metadata structure
- Intelligently throttle API requests to minimize usage
- Leverage existing authentication and ingest infrastructure
- Provide utility functions for checking update status and managing refresh operations
- Design with database abstraction to support both SQLite and Neo4j backends
- Implement patterns similar to Neo4j's GraphRAG for efficient updates

### B. Metadata Storage Extensions

Extend the current metadata storage to track per-repository update timestamps:

- Use the existing metadata structure in graph.db
- Add source-specific timestamps (GitHub, Linear, etc.)
- Implement functions to read and write these timestamps
- Ensure backward compatibility with existing metadata
- Design metadata schema to be compatible with Neo4j's property graph model
- Use similar patterns to Neo4j's LLM Graph Builder for tracking document updates

### C. Refresh Command for Cron Jobs

Create a dedicated refresh command optimized for scheduled execution:

- Implement as a standalone CLI command (`arc refresh`)
- Add silent mode option for automated execution
- Include error handling and retry logic
- Implement adaptive throttling based on API rate limits
- Design for efficient execution in scheduled environments (cron, Task Scheduler, launchd)

### D. Enhanced PR Processing

Extend the existing PR processing to extract more decision context:

- Use the Ollama client from `semantic_search.py` to generate decision summaries
- Add specific PR processing that focuses on identifying decision rationale
- Store enhanced PR descriptions in the node's extra data
- Implement prompt templates optimized for extracting decision context
- Adopt techniques from Neo4j's LLM Graph Builder for entity and relationship extraction
- Design extraction schema for causal relationships (decision > implication > code-change)
- Implement chunking and embedding generation for improved semantic search

### E. CLI Status Command (`arc_memory/cli/status.py`)

Create a new CLI command to show the auto-refresh service status:

- Display last refresh time and pending updates
- Show configuration settings (check interval, enabled sources)
- Provide statistics on auto-refreshed data
- Include troubleshooting information if errors occur

## 3. Integration Points

1. **CLI Integration**: Add a new `refresh` command to the main CLI for scheduled execution
2. **Build Process**: Leverage the existing incremental build capabilities in the build command
3. **Authentication**: Use the existing authentication infrastructure (`get_installation_token_for_repo`, `get_github_token`)
4. **Data Fetching**: Utilize the existing `GitHubFetcher` and `LinearIngestor` classes for data retrieval
5. **Database Access**: Use the existing database connection and query functions
6. **System Scheduling**: Provide documentation for setting up scheduled tasks on different platforms (cron, Task Scheduler, launchd)

## 4. Implementation Strategy

1. **Phase 1**: Implement the core refresh command with GitHub support and database abstraction
   - Create the `arc refresh` command with silent mode option
   - Implement GitHub polling using existing ingestors
   - Add metadata tracking for update timestamps
   - Design database abstraction layer for SQLite and Neo4j compatibility
   - Implement SQLite adapter first with Neo4j-compatible patterns

2. **Phase 2**: Add enhanced PR processing with LLM integration
   - Implement decision context extraction from PR descriptions
   - Create optimized prompts for the Ollama client
   - Store enhanced descriptions in the knowledge graph
   - Adopt Neo4j LLM Graph Builder techniques for entity and relationship extraction
   - Implement chunking and embedding generation for improved semantic search

3. **Phase 3**: Add Linear support and status command
   - Extend the refresh command to support Linear data
   - Implement the status command for monitoring
   - Add configuration options for controlling refresh behavior
   - Ensure compatibility with both SQLite and Neo4j backends
   - Design unified status reporting for both backends

4. **Phase 4**: Optimize, document, and prepare for Neo4j integration
   - Implement intelligent API throttling
   - Create documentation for setting up scheduled tasks on different platforms
   - Optimize performance and resource usage for scheduled execution
   - Prepare for Neo4j integration in the cloud offering
   - Implement Neo4j adapter using GraphRAG patterns

## 5. User Experience

- Users authenticate once with `arc auth gh` (already implemented)
- Users set up a scheduled task to run `arc refresh --silent` at their preferred interval
- The refresh command runs automatically according to the schedule, updating the graph
- When users run `arc why query`, they get results from the most current data
- Users can check status with `arc status` to see last refresh time and pending updates
- Configuration options allow customizing refresh behavior and enabled sources

## 6. Technical Considerations

- **Exit Codes**: Ensure proper exit codes for scheduled task monitoring
- **Resource Usage**: Minimize memory and CPU usage during refresh operations
- **Error Handling**: Implement robust error handling and logging for unattended execution
- **API Rate Limits**: Respect GitHub and Linear API rate limits
- **Backward Compatibility**: Maintain compatibility with existing commands and workflows
- **Cross-Platform Support**: Ensure the refresh command works consistently across operating systems
- **Database Abstraction**: Design for both SQLite and Neo4j backends
- **Neo4j Compatibility**: Ensure metadata schema is compatible with Neo4j's property graph model
- **Incremental Updates**: Optimize for efficient incremental updates in both backends
- **Transaction Support**: Use transaction capabilities for atomic updates

## 7. Data Flow Diagram

```bash
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  System         │     │  Arc CLI        │     │  Knowledge      │
│  Scheduler      │     │  Commands       │     │  Graph          │
│  (cron/Task     │     │                 │     │  (SQLite DB)    │
│  Scheduler)     │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │                       │                       │
         │  Scheduled            │                       │
         │  Execution            │                       │
         │                       │                       │
         ▼                       │                       │
┌─────────────────┐             │                       │
│                 │             │                       │
│  arc refresh    │             │                       │
│  --silent       │             │                       │
│                 │             │                       │
└────────┬────────┘             │                       │
         │                       │                       │
         │                       │                       │
         │  Uses                 │  Uses                 │
         ▼                       ▼                       │
┌─────────────────┐     ┌─────────────────┐             │
│                 │     │                 │             │
│  auto_refresh.py│     │  arc status     │             │
│  Core Logic     │     │  Command        │             │
│                 │     │                 │             │
└────────┬────────┘     └────────┬────────┘             │
         │                       │                       │
         │                       │                       │
         │  Updates              │  Reads                │
         ▼                       ▼                       │
┌─────────────────┐     ┌─────────────────┐             │
│                 │     │                 │             │
│  Metadata       │◄────┤  Last Update    │◄────────────┘
│  Storage        │     │  Timestamps     │
│                 │     │                 │
└────────┬────────┘     └─────────────────┘
         │
         │
         │  Triggers
         ▼
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│  Incremental    │     │  External APIs  │
│  Build Process  │◄────┤  (GitHub,       │
│                 │     │  Linear)        │
└────────┬────────┘     └─────────────────┘
         │
         │
         │  Updates
         ▼
┌─────────────────┐
│                 │
│  Knowledge      │
│  Graph          │
│  (Nodes/Edges)  │
│                 │
└─────────────────┘
```

This implementation plan builds directly on the existing codebase, leveraging the authentication, fetching, and processing logic already in place while adding scheduled refresh capabilities through system task schedulers. It also prepares for future Neo4j integration in the cloud offering by designing with database abstraction from the beginning and adopting patterns from Neo4j's GraphRAG Python Package and LLM Graph Builder.

## 8. Neo4j Integration Path

To ensure a smooth transition from local SQLite to cloud Neo4j, we'll implement the following:

1. **Database Abstraction Layer**:
   - Create interfaces that work with both SQLite and Neo4j
   - Implement SQLite adapter first with Neo4j-compatible patterns
   - Add Neo4j adapter using GraphRAG patterns when needed

2. **Metadata Compatibility**:
   - Design metadata schema to be compatible with Neo4j's property graph model
   - Use similar patterns to Neo4j's LLM Graph Builder for tracking document updates
   - Ensure efficient incremental updates in both backends

3. **GraphRAG Integration**:
   - Adopt techniques from Neo4j's LLM Graph Builder for entity and relationship extraction
   - Implement chunking and embedding generation for improved semantic search
   - Prepare for vector search capabilities in the Neo4j backend

This approach ensures that our auto-refresh functionality will work seamlessly with both our local SQLite implementation and our future Neo4j-based cloud offering, while leveraging the best practices and patterns from Neo4j's GenAI ecosystem.
