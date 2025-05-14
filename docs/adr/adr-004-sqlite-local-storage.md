---
title: Use SQLite for Local Knowledge Graph Storage
date: 2025-05-14
status: accepted
decision_makers: ["Jarrod Barnes", "Engineering Team"]
---

# Use SQLite for Local Knowledge Graph Storage

## Context

Arc Memory needs a storage solution for the local knowledge graph that balances several requirements:

- **Developer Experience**: The solution should be easy to set up and use, with minimal configuration required.
- **Performance**: The solution should provide good query performance for knowledge graph operations.
- **Portability**: The solution should work across different operating systems and environments.
- **Embeddability**: The solution should be embeddable in the application without requiring separate server setup.
- **SQL Support**: The solution should support SQL queries for flexible data access.
- **Local-First**: The solution should prioritize local operation to maintain privacy and performance.

We considered several options including:
1. SQLite
2. PostgreSQL
3. Neo4j
4. LevelDB/RocksDB
5. In-memory databases

## Decision

We will use SQLite as the primary storage backend for Arc Memory's local knowledge graph.

This decision aligns with our local-first philosophy and enables a frictionless developer experience while still providing a path to cloud integration in the future.

## Consequences

### Positive

- **Zero Configuration**: SQLite requires no separate database server setup, reducing the barrier to entry for new users.
- **Portability**: SQLite databases are single files that can be easily backed up, moved, or shared.
- **Embeddability**: SQLite can be embedded directly in the application, simplifying deployment.
- **SQL Support**: SQLite provides robust SQL query capabilities for flexible data access.
- **Performance**: SQLite offers good performance for read-heavy workloads, which matches our primary use case.
- **Reliability**: SQLite is known for its reliability and data integrity guarantees.
- **Widespread Adoption**: SQLite is one of the most widely deployed database engines, with extensive documentation and community support.
- **Path to Cloud**: Our database abstraction layer allows for future integration with cloud-based solutions like Neo4j.

### Negative

- **Limited Concurrency**: SQLite has limited support for concurrent write operations, which could be a bottleneck in multi-user scenarios.
- **Not Distributed**: SQLite is not designed for distributed deployments, which limits scalability for very large teams.
- **Graph Queries**: While SQLite supports SQL, it doesn't have native graph query capabilities like Neo4j, requiring us to implement graph traversal logic in application code.
- **Migration Path**: Eventually, users may need to migrate to a more robust solution as their scale increases, which will require additional tooling.

### Mitigations

To address the limitations of SQLite:

1. **Database Abstraction Layer**: We've implemented a database abstraction layer that allows us to potentially support other database backends in the future, including Neo4j for Arc Cloud.

2. **Optimized Schema Design**: We've designed our schema to optimize for SQLite's strengths and mitigate its weaknesses, particularly for graph traversal operations.

3. **Selective Sync**: For team collaboration, we'll implement a selective sync mechanism that allows local SQLite databases to synchronize with a cloud-based Neo4j instance, combining the benefits of both approaches.

4. **Incremental Builds**: To address performance concerns with large repositories, we've implemented incremental build capabilities that minimize the amount of data that needs to be processed and stored.

## Implementation Notes

The SQLite implementation will be encapsulated behind a database adapter interface, allowing for potential future support of alternative storage backends. This adapter will handle:

- Connection management
- Schema creation and migration
- Graph traversal operations
- Query optimization
- Caching strategies

This approach gives us the benefits of SQLite's simplicity and embeddability while maintaining flexibility for future enhancements.
