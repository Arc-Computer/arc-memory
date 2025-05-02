We're thrilled to announce the release of Arc Memory SDK v0.1.0, the first stable release of our open-source foundation for software engineering memory. 

## **The Problem We're Solving**

Software engineering is fundamentally a collaborative, knowledge-intensive process. Yet the tools we use to build software are primarily focused on the "what" and "how" of code, leaving the crucial "why" scattered across pull requests, issues, documentation, and team communications.

This fragmentation creates significant challenges:

- **Knowledge loss** when team members leave or switch projects
- **Onboarding friction** for new developers trying to understand existing code
- **Decision amnesia** where teams repeat past mistakes or reinvent solutions
- **Context switching** as developers hunt for information across multiple tools
- **Agent limitations** where AI assistants lack the historical context to provide truly helpful guidance

Arc Memory addresses these challenges by creating a unified, temporal knowledge graph that connects code to its full context and history.

## **Introducing Arc Memory SDK**

Arc Memory SDK is a comprehensive Python toolkit that embeds a local, bi-temporal knowledge graph (TKG) in every developer's workspace. It surfaces verifiable decision trails during code review and exposes the same provenance to any LLM-powered agent through VS Code's Agent Mode.

### **Key Features**

- **Extensible Plugin Architecture**: Easily add new data sources beyond Git, GitHub, and ADRs
- **Comprehensive Knowledge Graph**: Build a local graph from Git commits, GitHub PRs, issues, and ADRs
- **Trace History Algorithm**: Fast BFS algorithm to trace history from file+line to related entities
- **High Performance**: Trace history queries complete in under 200ms (typically ~100μs)
- **Incremental Builds**: Efficiently update the graph with only new data
- **Rich CLI**: Command-line interface for building graphs and tracing history
- **Privacy-First**: All data stays on your machine; no code or IP leaves your repo
- **CI Integration**: Team-wide graph updates through CI workflows

### **Getting Started**

Installation is straightforward with Python 3.10 or higher:

```bash
pip install arc-memory

# Authenticate with GitHub (one-time)
arc auth gh

# Build your knowledge graph
arc build

# Check the status
arc doctor

# Trace history
arc trace file path/to/file.py 42
```

## **The Arc Memory Ecosystem**

The SDK we're releasing today is just the first component of a broader ecosystem we're building:

### **1. Arc Memory SDK (Available Now)**

The core Python SDK and CLI provides the foundation for building and querying the knowledge graph. It's designed to be lightweight, extensible, and privacy-focused, keeping all your data local.

### **2. Arc Memory MCP Server (Coming Soon)**

Our upcoming Model Context Protocol (MCP) server will integrate with Anthropic's open standard for connecting AI assistants to data sources:

- **Standardized AI Access**: Following Anthropic's MCP specification for secure, standardized AI access to knowledge graphs
- **Persistent Memory**: Knowledge graph-based persistent memory system for AI agents
- **Contextual Retrieval**: Intelligent retrieval of relevant code history and decisions
- **Seamless Integration**: Works with Claude and other MCP-compatible AI assistants
- **Privacy Controls**: Fine-grained access controls for sensitive information
- **Verifiable Citations**: Enables AI to cite specific evidence from the knowledge graph

This will allow any MCP-compatible AI assistant to access your codebase's memory and context, providing deeper insights and more accurate assistance.

### **3. VS Code Extension (Coming Soon)**

Our VS Code extension will bring the power of Arc Memory directly into your development environment:

- Hover cards showing the decision trail behind code
- Inline context for functions, classes, and variables
- Integration with VS Code's Agent Mode for AI-assisted development
- Visual exploration of the knowledge graph
- Quick access to related PRs, issues, and documentation

## **The Foundation for AI-Assisted Development**

Arc Memory is designed from the ground up to be the memory layer for AI-assisted development. By providing structured, verifiable context about code history and decisions, it enables AI agents to:

1. **Understand code in context** - not just what it does, but why it was written that way
2. **Reference relevant discussions** - pointing to PRs, issues, and ADRs that explain decisions
3. **Avoid repeating mistakes** - by having access to the full history of changes and their rationale
4. **Generate better suggestions** - grounded in the project's actual history and patterns
5. **Verify its own reasoning** - by citing specific evidence from the knowledge graph

## **Open Source Foundation**

Arc Memory SDK is released under the MIT license, reflecting our commitment to building in the open. We believe that the memory layer for software engineering should be:

1. **Open and extensible** - allowing integration with any tool or workflow
2. **Privacy-respecting** - keeping sensitive code and discussions local
3. **Community-driven** - evolving based on real-world developer needs
4. **Interoperable** - working with existing tools rather than replacing them

While the SDK is fully open source, our future commercial offerings will build on this foundation with team features, enterprise integrations, and advanced capabilities.

## **Get Involved**

We're just getting started, and we'd love your involvement:

- **Try it out**: Install the SDK and build your first knowledge graph
- **Give feedback**: Open issues on GitHub with bugs, feature requests, or ideas
- **Contribute**: The codebase is open source and we welcome contributions
- **Spread the word**: Tell your colleagues about Arc Memory

Visit our [GitHub repository](https://github.com/Arc-Computer/arc-memory) to get started, or check out our [documentation](https://docs.arc.computer/) for detailed guides.

## **What's Next**

This initial release is just the beginning. Our roadmap includes:

- Additional data source plugins (Notion, Jira, Linear, G-Suite)
- Enhanced visualization capabilities
- Team collaboration features
- Advanced query capabilities
- Deeper IDE integration
- AI agent-specific APIs

Stay tuned for regular updates as we build the memory layer for the future of software engineering.