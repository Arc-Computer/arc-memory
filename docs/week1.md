# Week 1 Implementation Plan

## Priority Tasks

1. **GitHub App Integration**
   - Update GitHub App Configuration
   - Implement JWT Generation
   - Add Installation Token Support
   - Update CLI Commands

2. **Trace History Algorithm**
   - Implement Git Blame Integration
   - Implement Graph Traversal
   - Optimize for Performance
   - Add Result Formatting

3. **Comprehensive Tests**
   - Set Up Test Infrastructure
   - Add Unit Tests for Core Modules
   - Add Integration Tests
   - Measure and Improve Coverage

4. **Plugin Architecture**
   - Define Plugin Interface
   - Create Plugin Registry
   - Refactor Existing Ingestors
   - Add Plugin Discovery

## Detailed Implementation Steps

### 1. Completing the GitHub App Integration

#### Step 1.1: Update GitHub App Configuration
- Create a `GitHubAppConfig` model to store app credentials (app ID, private key, client ID, client secret)
- Add functions to load these credentials from environment variables or a config file

#### Step 1.2: Implement JWT Generation
- Enhance the existing JWT generation code to create tokens for GitHub App authentication
- Add functionality to exchange JWT for installation tokens

#### Step 1.3: Add Installation Token Support
- Implement functions to get installation IDs for repositories
- Add code to exchange JWTs for installation tokens
- Update the token discovery order to include GitHub App tokens

#### Step 1.4: Update CLI Commands
- Enhance `arc auth gh` to support GitHub App authentication
- Add options to register a GitHub App installation

### 2. Implementing the Trace History Algorithm

#### Step 2.1: Implement Git Blame Integration
- Add functionality to map file+line to commit using git blame
- Handle edge cases (deleted files, renamed files)

#### Step 2.2: Implement Graph Traversal
- Implement the two-hop BFS algorithm
- Follow the edge relationships as specified:
  - Commit → PR via MERGES
  - PR → Issue via MENTIONS
  - Issue → ADR via DECIDES

#### Step 2.3: Optimize for Performance
- Ensure the query meets the 200ms latency target
- Add caching if necessary

#### Step 2.4: Add Result Formatting
- Format the results as specified in the API docs
- Limit to max 3 nodes, newest first

### 3. Adding More Comprehensive Tests

#### Step 3.1: Set Up Test Infrastructure
- Create test fixtures for common test scenarios
- Set up mocks for external dependencies (GitHub API, git)

#### Step 3.2: Add Unit Tests for Core Modules
- Write tests for schema models
- Write tests for SQL operations
- Write tests for ingestors
- Write tests for CLI commands

#### Step 3.3: Add Integration Tests
- Create tests that verify the end-to-end flow
- Test incremental builds with real repositories

#### Step 3.4: Measure and Improve Coverage
- Set up coverage reporting
- Identify and fill coverage gaps

### 4. Implementing the Plugin Architecture

#### Step 4.1: Define Plugin Interface
- Create a protocol/interface for ingestor plugins
- Define required methods (get_name, get_node_types, get_edge_types, ingest)

#### Step 4.2: Create Plugin Registry
- Implement a registry to manage and discover plugins
- Add methods to register and retrieve plugins

#### Step 4.3: Refactor Existing Ingestors
- Convert existing ingestors (git, github, adr) to use the plugin interface
- Ensure they maintain all current functionality

#### Step 4.4: Add Plugin Discovery
- Implement entry point discovery for third-party plugins
- Add documentation on how to create and register plugins

## Timeline and Milestones

### Week 1 Deliverables
- GitHub App auth helper
- `arc build` output with basic functionality
- Initial implementation of trace history algorithm
- Foundation for comprehensive tests
- Design of plugin architecture

### Success Criteria
- Users can authenticate with GitHub App
- Users can build a knowledge graph from Git, GitHub, and ADRs
- Basic trace history queries work
- Test coverage is at least 50% (on track to 80%)
- Plugin architecture design is documented
