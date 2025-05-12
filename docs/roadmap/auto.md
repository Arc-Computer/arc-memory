# Implementation Plan for Auto-Refreshing Knowledge Graph

Based on the existing codebase structure, this document outlines a detailed implementation plan for adding auto-refresh capabilities to Arc Memory, with considerations for both SQLite (local) and Neo4j (cloud) backends.

## 1. Overview

The auto-refresh functionality will enable Arc Memory to proactively update its knowledge graph on a schedule, ensuring users always have access to the most current information without manually running `arc build --incremental`. This will be implemented by creating a dedicated refresh command that can be scheduled using system tools (cron, Task Scheduler, launchd) to periodically check for new data from configured sources (primarily GitHub) and trigger incremental updates when changes are detected.

### Implementation Focus

Based on our resource constraints and prioritization:

- The initial implementation will focus exclusively on SQLite for local usage
- We'll prioritize GitHub as the primary data source for the first release
- The design will include hooks for future Neo4j integration, but implementation will be deferred
- We'll keep the initial implementation lightweight and reliable rather than feature-rich

## 2. Key Components

### A. Auto-Refresh Module (`arc_memory/auto_refresh.py`)

This will be the core module responsible for managing the refresh process:

- Implement core refresh functionality that can be called from the CLI
- Track per-repository update timestamps in the existing metadata structure
- Implement conservative throttling for API requests to respect rate limits
- Leverage existing authentication and ingest infrastructure
- Provide utility functions for checking update status and managing refresh operations
- Design with future extensibility in mind, but focus on SQLite implementation
- Keep the implementation simple and reliable

### B. Metadata Storage Extensions

Extend the current metadata storage to track per-repository update timestamps:

- Use the existing metadata structure in graph.db
- Add source-specific timestamps (primarily GitHub)
- Implement functions to read and write these timestamps
- Ensure backward compatibility with existing metadata
- Keep the schema simple and focused on immediate needs
- Design with clean interfaces that could support other backends later

### C. Refresh Command for Cron Jobs

Create a dedicated refresh command optimized for scheduled execution:

- Implement as a standalone CLI command (`arc refresh`)
- Add silent mode option for automated execution
- Include error handling and retry logic
- Implement adaptive throttling based on API rate limits
- Design for efficient execution in scheduled environments (cron, Task Scheduler, launchd)

### D. Basic PR Processing

Extend the existing PR processing to capture essential context:

- Use the existing PR processing infrastructure
- Focus on capturing basic metadata and relationships
- Store PR descriptions in the node's data
- Keep LLM enhancements minimal for the initial release
- Defer more advanced extraction techniques for future releases
- Prioritize reliability and performance over advanced features

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

1. **Phase 1**: Implement the core refresh command with GitHub support
   - Create the `arc refresh` command with silent mode option
   - Implement GitHub polling using existing ingestors
   - Add metadata tracking for update timestamps
   - Focus on SQLite implementation with clean interfaces
   - Ensure reliable operation with conservative defaults

2. **Phase 2**: Add basic status command and documentation
   - Implement the status command for monitoring
   - Create documentation for setting up scheduled tasks on different platforms
   - Add configuration options for controlling refresh behavior
   - Implement basic error handling and logging
   - Test thoroughly with different usage patterns

3. **Phase 3**: Optimize and enhance (if needed)
   - Refine API throttling based on real-world usage
   - Optimize performance and resource usage for scheduled execution
   - Address any issues identified during initial usage
   - Consider adding git hooks as an alternative trigger mechanism
   - Improve documentation based on user feedback

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

This implementation plan builds directly on the existing codebase, leveraging the authentication, fetching, and processing logic already in place while adding scheduled refresh capabilities through system task schedulers. It focuses on delivering a reliable, lightweight solution that addresses the immediate need for automatic knowledge graph updates while setting the stage for future enhancements.

## 8. Future Extensibility

While focusing on a lightweight initial implementation, we'll design with future extensibility in mind:

1. **Clean Interfaces**:
   - Create well-defined interfaces for data access and storage
   - Use dependency injection where appropriate
   - Avoid tight coupling to SQLite-specific features
   - Document extension points for future developers

2. **Metadata Design**:
   - Keep metadata schema simple but extensible
   - Use standard data formats that can be easily migrated
   - Document the schema for future reference

3. **Deferred Enhancements**:
   - Linear integration
   - Advanced LLM-based PR processing
   - Neo4j integration for cloud offering
   - More sophisticated scheduling options

This approach ensures that our auto-refresh functionality delivers immediate value with a reliable implementation while setting the stage for future enhancements as resources allow.
