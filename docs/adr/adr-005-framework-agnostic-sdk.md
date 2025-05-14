---
title: Framework-Agnostic SDK Design
date: 2025-05-14
status: accepted
decision_makers: ["Jarrod Barnes", "Engineering Team"]
---

# Framework-Agnostic SDK Design

## Context

As AI agent frameworks proliferate, developers are using a variety of tools and libraries to build their applications, including:

- LangChain
- OpenAI Assistants API
- Anthropic Claude
- Custom agent implementations
- LlamaIndex
- AutoGen
- CrewAI

To maximize adoption and utility, Arc Memory needs to integrate seamlessly with these diverse frameworks while maintaining a clean, consistent API. We need to decide whether to:

1. Tightly integrate with a specific framework (e.g., LangChain)
2. Create a framework-agnostic SDK with adapters for different frameworks
3. Implement multiple framework-specific SDKs

## Decision

We will implement a framework-agnostic SDK with adapters for different agent frameworks.

The core SDK will expose a clean, consistent API that focuses on knowledge graph operations, while framework-specific adapters will handle the integration with different agent frameworks.

## Consequences

### Positive

- **Maximum Flexibility**: Developers can use Arc Memory with their framework of choice, or directly with the core SDK.
- **Future-Proofing**: As new frameworks emerge or existing ones evolve, we can add new adapters without changing the core SDK.
- **Consistent Experience**: The core SDK provides a consistent experience regardless of the framework being used.
- **Reduced Coupling**: The core SDK is not tied to the lifecycle or design decisions of any specific framework.
- **Simplified Testing**: The core SDK can be tested independently of any framework integration.
- **Composability**: Functions from the SDK can be composed in different ways to support various use cases.
- **Broader Adoption**: By supporting multiple frameworks, we can reach a wider audience of developers.

### Negative

- **Increased Development Effort**: We need to develop and maintain adapters for multiple frameworks.
- **Abstraction Overhead**: The adapter layer adds some complexity to the codebase.
- **Framework-Specific Optimizations**: Some framework-specific optimizations may be harder to implement with a generic adapter approach.
- **Documentation Complexity**: We need to document both the core SDK and each adapter.

### Mitigations

To address these challenges:

1. **Adapter Registry**: We've implemented an adapter registry that allows for dynamic discovery and registration of framework adapters.

2. **Protocol-Based Design**: We've defined clear protocols (interfaces) for adapters to implement, ensuring consistency across different frameworks.

3. **Entry Points**: We use Python entry points to allow third-party packages to register their own adapters, enabling ecosystem growth.

4. **Comprehensive Examples**: We provide comprehensive examples for each supported framework to simplify integration.

5. **Prioritization**: We initially focus on the most popular frameworks (LangChain, OpenAI) while designing the adapter system to be extensible.

## Implementation Details

The framework-agnostic design is implemented through:

1. **Core SDK**: A clean, consistent API for knowledge graph operations that doesn't depend on any specific agent framework.

2. **Adapter Protocol**: A well-defined protocol that adapters must implement to integrate with a specific framework.

3. **Adapter Registry**: A registry that manages available adapters and allows for dynamic discovery.

4. **Framework-Specific Adapters**: Implementations of the adapter protocol for specific frameworks like LangChain and OpenAI.

5. **Conversion Functions**: Functions that convert between Arc Memory's data structures and framework-specific formats.

6. **Tool Creation**: Methods to create framework-specific tools from Arc Memory functions.

7. **Agent Creation**: Helper methods to create agents using the framework with Arc Memory tools.

This approach allows developers to use Arc Memory in a way that feels natural for their chosen framework while maintaining a consistent core experience.
