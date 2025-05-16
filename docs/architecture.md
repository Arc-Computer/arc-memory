# Arc Memory Architecture

Arc Memory is built around a bi-temporal knowledge graph that captures the evolution of code and the decisions behind it. This document explains the core architecture, design principles, and key components of the system.

## System Overview

```bash
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Data Sources  │     │ Knowledge Graph │     │    Interfaces   │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│                 │     │                 │     │                 │
│  Git Repository ├────►│                 │     │  CLI Commands   │
│                 │     │                 │     │  - arc query    │
│  GitHub Issues  ├────►│   Bi-Temporal   ├────►│  - arc why      │
│  & Pull Requests│     │   Knowledge     │     │  - arc relate   │
│                 │     │     Graph       │     │                 │
│  Linear Tickets ├────►│                 │     │  SDK Methods    │
│                 │     │                 │     │  - arc.query()  │
│  ADRs           ├────►│                 │     │  - arc.get_     │
│                 │     │                 │     │    decision_    │
│  Custom Sources ├────►│                 │     │    trail()      │
│  (via plugins)  │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Agent Adapters │
                        ├─────────────────┤
                        │                 │
                        │  LangChain      │
                        │                 │
                        │  OpenAI         │
                        │                 │
                        │  Custom         │
                        │  Frameworks     │
                        │                 │
                        └─────────────────┘
```

## Core Design Principles

1. **Local-First**: Arc Memory runs locally by default, ensuring privacy and performance.
2. **Bi-Temporal Modeling**: Tracks both when something happened (valid time) and when it was recorded (transaction time).
3. **Causal Relationships**: Captures the "why" behind code changes through causal connections.
4. **Plugin Architecture**: Extensible through plugins for data sources, storage, and analysis.
5. **Framework Agnostic**: Designed to work with any agent framework through adapters.
6. **Multi-Repository Support**: Analyzes across repository boundaries for comprehensive understanding.

## Key Components

### 1. Data Ingestion Layer

The data ingestion layer collects information from various sources and transforms it into a unified format for the knowledge graph:

```bash
┌─────────────────────────────────────────────────────────────┐
│                    Data Ingestion Layer                     │
├─────────────┬─────────────┬─────────────┬─────────────┬─────┤
│ Git Parser  │ GitHub API  │ Linear API  │ ADR Parser  │ ... │
└─────────────┴─────────────┴─────────────┴─────────────┴─────┘
```

- **Git Parser**: Extracts commits, branches, tags, and file changes
- **GitHub API**: Retrieves issues, pull requests, and comments
- **Linear API**: Collects tickets, projects, and team information
- **ADR Parser**: Processes Architectural Decision Records
- **Plugin Interface**: Allows for custom data source integration

### 2. Knowledge Graph Core

The knowledge graph core is the central component that stores and manages the relationships between entities:

```bash
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Graph Core                     │
├─────────────┬─────────────┬─────────────┬─────────────┬─────┤
│ Nodes       │ Edges       │ Properties  │ Temporal    │ ... │
│ (Entities)  │ (Relations) │             │ Tracking    │     │
└─────────────┴─────────────┴─────────────┴─────────────┴─────┘
```

- **Nodes**: Represent entities like files, functions, commits, issues, etc.
- **Edges**: Represent relationships between entities (calls, imports, modifies, etc.)
- **Properties**: Store metadata about nodes and edges
- **Temporal Tracking**: Records valid time and transaction time for bi-temporal queries
- **Repository Tagging**: Tags nodes with their source repository for multi-repository support

### 3. Storage Layer

Arc Memory supports multiple storage backends through a plugin architecture:

```bash
┌─────────────────────────────────────────────────────────────┐
│                       Storage Layer                         │
├─────────────────────────┬─────────────────────────┬─────────┤
│ SQLite (Local)          │ Neo4j (Cloud)           │ ...     │
└─────────────────────────┴─────────────────────────┴─────────┘
```

- **SQLite**: Default local storage for individual developers
- **Neo4j**: Optional cloud storage for team collaboration
- **Adapter Pattern**: Common interface for all storage backends
- **Migration Tools**: Utilities for moving between storage backends

### 4. Query Engine

The query engine provides powerful ways to extract insights from the knowledge graph:

```bash
┌─────────────────────────────────────────────────────────────┐
│                       Query Engine                          │
├─────────────┬─────────────┬─────────────┬─────────────┬─────┤
│ Natural     │ Decision    │ Entity      │ Impact      │ ... │
│ Language    │ Trail       │ Relation    │ Analysis    │     │
└─────────────┴─────────────┴─────────────┴─────────────┴─────┘
```

- **Natural Language**: Answers questions about the codebase in natural language
- **Decision Trail**: Traces the history and rationale behind specific code
- **Entity Relation**: Finds connections between entities in the graph
- **Impact Analysis**: Predicts the potential impact of changes
- **Temporal Queries**: Enables "time travel" through the codebase's history

### 5. SDK and CLI

The SDK and CLI provide interfaces for interacting with Arc Memory:

```bash
┌─────────────────────────────────────────────────────────────┐
│                       SDK and CLI                           │
├─────────────────────────┬─────────────────────────┬─────────┤
│ Python SDK              │ Command Line Interface  │ ...     │
└─────────────────────────┴─────────────────────────┴─────────┘
```

- **Python SDK**: Programmatic access to Arc Memory functionality
- **Command Line Interface**: Direct interaction through terminal commands
- **Framework Adapters**: Integration with agent frameworks like LangChain and OpenAI

### 6. Framework Adapters

The framework adapters enable integration with various agent frameworks:

```bash
┌─────────────────────────────────────────────────────────────┐
│                    Framework Adapters                       │
├─────────────┬─────────────┬─────────────┬─────────────┬─────┤
│ LangChain   │ OpenAI      │ Custom      │ ...         │     │
└─────────────┴─────────────┴─────────────┴─────────────┴─────┘
```

- **LangChain**: Adapts Arc Memory functions to LangChain tools
- **OpenAI**: Adapts Arc Memory functions to OpenAI function calling
- **Custom Adapters**: Interface for creating custom framework integrations

## Bi-Temporal Data Model

Arc Memory's bi-temporal data model is a key differentiator that enables powerful temporal reasoning:

```bash
┌─────────────────────────────────────────────────────────────┐
│                   Bi-Temporal Data Model                    │
├─────────────────────────┬─────────────────────────┬─────────┤
│ Valid Time              │ Transaction Time        │ ...     │
└─────────────────────────┴─────────────────────────┴─────────┘
```

- **Valid Time**: When something happened in the real world
- **Transaction Time**: When it was recorded in the system
- **Time Travel Queries**: Answer questions like "What did we know about X at time Y?"
- **Historical Analysis**: Track how entities evolved over time

## Multi-Repository Architecture

Arc Memory's multi-repository support enables analysis across repository boundaries:

```bash
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Repositories   │     │ Knowledge Graph │     │    Queries      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│                 │     │                 │     │                 │
│  Repository 1   ├────►│                 │     │  Single-Repo    │
│  (repo_id: A)   │     │                 │     │  Queries        │
│                 │     │                 │     │                 │
│  Repository 2   ├────►│  Unified Graph  ├────►│  Cross-Repo     │
│  (repo_id: B)   │     │  with Tagged    │     │  Queries        │
│                 │     │  Nodes          │     │                 │
│  Repository 3   ├────►│                 │     │  Filtered       │
│  (repo_id: C)   │     │                 │     │  Queries        │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

- **Repository Identity**: Each repository has a unique ID based on its path
- **Unified Graph**: All repositories share a single knowledge graph
- **Node Tagging**: Nodes are tagged with their source repository
- **Cross-Repository Edges**: Edges can connect nodes from different repositories
- **Filtered Queries**: Queries can be scoped to specific repositories

## Plugin Architecture

Arc Memory's plugin architecture enables extensibility at multiple levels:

```bash
┌─────────────────────────────────────────────────────────────┐
│                     Plugin Architecture                     │
├─────────────┬─────────────┬─────────────┬─────────────┬─────┤
│ Data Source │ Storage     │ Analysis    │ Framework   │ ... │
│ Plugins     │ Plugins     │ Plugins     │ Adapters    │     │
└─────────────┴─────────────┴─────────────┴─────────────┴─────┘
```

- **Data Source Plugins**: Add support for new data sources
- **Storage Plugins**: Add support for new storage backends
- **Analysis Plugins**: Add new analysis capabilities
- **Framework Adapters**: Add support for new agent frameworks

Arc Memory's architecture is designed to provide a comprehensive solution for preserving and leveraging engineering knowledge. The bi-temporal knowledge graph, plugin architecture, and framework adapters create a flexible, powerful system that can adapt to different workflows and use cases.

The local-first approach with optional cloud integration ensures that Arc Memory can be used by individual developers while also supporting team collaboration. The multi-repository support enables analysis across repository boundaries, providing a comprehensive view of complex systems.

By capturing the "why" behind code changes and enabling powerful temporal reasoning, Arc Memory provides unique value that traditional code analysis tools cannot match.
