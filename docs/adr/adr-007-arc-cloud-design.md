---
title: Arc Cloud Design with Neo4j GraphRAG Integration
date: 2025-05-14
status: accepted
decision_makers: ["Jarrod Barnes", "Engineering Team"]
---

# Arc Cloud Design with Neo4j GraphRAG Integration

## Context

Arc Memory's strategy involves a dual-track approach:
1. An open-source local-first knowledge graph (current focus)
2. A cloud-based offering for team collaboration and advanced features (Arc Cloud)

As we plan the Arc Cloud implementation, we need to make key architectural decisions that balance:

- **Consistency with Local Experience**: Ensuring a smooth transition between local and cloud usage
- **Team Collaboration**: Enabling effective knowledge sharing across teams
- **Performance at Scale**: Supporting larger graphs and more complex queries
- **Advanced Features**: Providing capabilities beyond what's possible with local-only implementations
- **Development Efficiency**: Leveraging existing technologies where appropriate
- **Differentiation**: Maintaining our unique value proposition

We considered several approaches:
1. Building a custom cloud backend from scratch
2. Using SQLite with a sync layer for cloud storage
3. Using PostgreSQL with graph extensions
4. Using a dedicated graph database like Neo4j
5. Using a hybrid approach with multiple database technologies

## Decision

We will implement Arc Cloud using Neo4j as the primary graph database, with specific integration of Neo4j's GraphRAG capabilities for enhanced knowledge retrieval and reasoning.

This approach will be complemented by a selective sync mechanism that bridges local SQLite instances with the cloud Neo4j graph.

## Consequences

### Positive

- **Native Graph Capabilities**: Neo4j provides native graph database capabilities, optimizing performance for graph traversal operations.
- **GraphRAG Integration**: Neo4j's GraphRAG capabilities provide a solid foundation for combining graph-based and vector-based retrieval.
- **Scalability**: Neo4j is designed to scale for large graphs and complex queries, supporting team-wide collaboration.
- **Visualization**: Neo4j includes powerful visualization capabilities that can enhance the user experience.
- **Ecosystem**: Neo4j has a mature ecosystem with extensive documentation, tools, and community support.
- **Development Acceleration**: Leveraging Neo4j's GraphRAG capabilities accelerates our development timeline for advanced features.
- **Clear Differentiation**: The combination of temporal knowledge graph, Neo4j's capabilities, and our unique blast radius prediction creates clear differentiation from competitors.

### Negative

- **Increased Complexity**: Managing two different database technologies (SQLite locally, Neo4j in the cloud) adds complexity.
- **Sync Challenges**: Synchronizing between SQLite and Neo4j requires careful design to handle schema differences and conflict resolution.
- **Learning Curve**: Neo4j uses Cypher query language, which differs from SQL and requires additional expertise.
- **Operational Overhead**: Running and maintaining Neo4j instances adds operational complexity compared to simpler database options.
- **Cost Considerations**: Neo4j can be more expensive to operate than simpler database technologies, affecting our pricing model.

### Mitigations

To address these challenges:

1. **Database Abstraction Layer**: We'll extend our existing database abstraction layer to support both SQLite and Neo4j backends, providing a consistent API regardless of the underlying storage.

2. **Selective Sync Mechanism**: We'll implement a selective sync mechanism that allows developers to control what gets synchronized between local and cloud instances, balancing privacy, bandwidth, and collaboration needs.

3. **Phased Implementation**: We'll implement Arc Cloud in phases, starting with core functionality and gradually adding more advanced features:
   - Phase 1: Basic cloud infrastructure and manual sync
   - Phase 2: Enhanced functionality with automated sync and basic GraphRAG features
   - Phase 3: Advanced features including sophisticated blast radius prediction

4. **Neo4j GraphRAG Integration**: We'll leverage Neo4j's GraphRAG capabilities to accelerate development of advanced retrieval and reasoning features, rather than building these components from scratch.

## Implementation Details

The Arc Cloud implementation will include:

1. **Core Cloud Infrastructure**:
   - Neo4j Aura (managed Neo4j service) for the team graph
   - API server for graph access
   - Authentication using established solutions (Auth0)
   - Basic web interface for graph exploration

2. **Selective Sync Mechanism**:
   - Bidirectional sync between local SQLite and cloud Neo4j
   - Change-based rather than state-based synchronization
   - Conflict resolution with vector clocks
   - Bandwidth-efficient with delta encoding
   - End-to-end encrypted

3. **Neo4j GraphRAG Integration**:
   - Knowledge graph construction leveraging Neo4j's capabilities
   - Vector search and embeddings for semantic retrieval
   - Entity and relationship extraction
   - Hybrid retrieval combining graph and vector approaches

4. **Team Collaboration Features**:
   - Shared access to the knowledge graph
   - Team structures and permissions
   - Notification system for relevant changes
   - Collaborative annotations and insights

This approach allows us to deliver a compelling cloud offering that builds on our local-first foundation while adding powerful team collaboration capabilities and advanced features that differentiate us in the market.
