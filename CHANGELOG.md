# Changelog

All notable changes to the Arc Memory SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-11-15

### Added
- Automatic database migration when initializing the database
- Improved Ollama integration with better error handling and timeout support
- Enhanced documentation for Ollama dependency

### Fixed
- Fixed database schema issues with timestamp column
- Improved framework adapter registration and discovery
- Enhanced error messages for missing dependencies

## [0.4.2] - 2025-05-10

### Fixed
- Fixed redundant conditional check in JSON extraction function
- Improved defensive programming with `.get()` method calls for node attribute access
- Added type validation for decision_makers field to ensure it's always a list
- Enhanced error handling for incomplete data structures in the knowledge graph search

## [0.4.1] - 2025-05-09

### Fixed
- Fixed JavaScript/TypeScript LLM parsing errors by using a robust JSON extraction function
- Addressed PR feedback for consistent downstream processing in regex fallback
- Updated _extract_json_from_llm_response to handle responses with thinking sections
- Improved system prompt handling for LLMs
- Fixed temporal analysis error and standardized on Qwen3:4b model
- Fixed Node path field error in temporal_analysis
- Fixed FileNode properties handling in temporal_analysis
- Fixed JSON parsing and temporal analysis: added robust JSON extraction, fixed CommitNode property access, and improved Ollama client
- Fixed GitHub integration errors with proper null handling for PR and issue details

### Added
- Added system prompt to improve JSON generation for JavaScript/TypeScript analysis
- Added robust regex fallback for JavaScript/TypeScript analysis when JSON parsing fails
- Added script to create sample causal data for testing
- Enhanced Knowledge Graph of Thoughts (KGoT) implementation to better capture decision trails
- Implemented extraction of causal relationships from commit messages, PR descriptions, Linear tickets, and ADRs
- Added schema models for causal edge representation (decision → implication → code-change)

### Changed
- Use generate() instead of generate_with_thinking() to avoid thinking section in JSON response
- Optimized export for causal relationships
- Improved build command logging and switched to Qwen 3:4b model
- Improved CLI usability: Add --github flag and increase LLM timeout to 260 seconds
- Updated ingestor instantiation and parameter passing
- Improved build command structure to match CLI expectations
- Enhanced knowledge graph: improved Ollama client parsing, added system prompt, and fixed temporal analysis

## [0.3.1] - 2025-05-1

### Added
- New `arc sim` command for simulation-based impact prediction
- Implemented diff analysis to identify affected services from code changes
- Added causal graph derivation from the knowledge graph
- Integrated E2B for isolated sandbox environments
- Implemented fault injection with Chaos Mesh (network latency, CPU stress, memory stress)
- Created LangGraph workflow for orchestrating the simulation process
- Added risk assessment with metrics collection and analysis
- Implemented attestation generation with cryptographic verification
- Added comprehensive documentation for the `arc sim` command
- Created detailed examples for different simulation scenarios
- Added unit and integration tests for all simulation components

### Changed
- Refactored README to position simulation as the core differentiator
- Enhanced developer experience with clearer prerequisites and troubleshooting guidance
- Improved test isolation with proper mock resetting and fixture cleanup

## [0.3.0] - 2025-04-30

### Added
- Complete CLI implementation with a comprehensive set of commands
- New `arc why` command to understand why a file or commit exists
- New `arc relate` command to find relationships between entities in the graph
- New `arc serve` command to start the MCP server for IDE integration
- New `arc auth` command for GitHub authentication
- New `arc doctor` command to diagnose and fix issues
- New telemetry system with opt-in privacy controls (disabled by default)
- Improved GitHub GraphQL client with better rate limit handling
- Enhanced error handling and logging throughout the codebase
- Comprehensive test coverage for all CLI commands
- Added CI workflow for testing CLI commands across Python versions

### Changed
- Shifted to a CLI-first approach for better user experience
- Improved documentation with detailed command references
- Renamed from 'arc-memory SDK' to 'arc CLI' to better reflect its focus
- Updated GitHub GraphQL client to follow latest standards and best practices

### Fixed
- Fixed relationship type filtering in the `relate` command
- Fixed GitHub GraphQL tests to properly mock dependencies
- Improved error handling in authentication flows
- Enhanced rate limit handling with exponential backoff

## [0.2.2] - 2025-04-29

### Added
- Implemented GitHub ingestion with GraphQL and REST API clients
- Added PR and issue fetching with GraphQL for efficient bulk data retrieval
- Added REST API integration for specific operations (PR files, commits, reviews, comments)
- Added rate limit handling with backoff strategies
- Added batch processing capabilities for better performance
- Added comprehensive unit and integration tests for GitHub ingestion

## [0.2.1] - 2025-04-29

### Fixed
- Improved ADR date parsing to handle YAML date objects correctly
- Fixed version reporting consistency across the codebase
- Enhanced error messages for GitHub authentication

## [0.2.0] - 2025-04-28

### Added
- New `ensure_connection()` function to handle both connection objects and paths
- Comprehensive API documentation for database functions
- Detailed ADR formatting guide with examples
- Enhanced troubleshooting guide with common error solutions

### Fixed
- GitHub authentication issues with Device Flow API endpoints
- Added fallback mechanism for GitHub authentication
- Improved ADR date parsing with better error messages
- Standardized database connection handling across functions
- Enhanced error messages with actionable guidance

## [0.1.5] - 2025-04-25

### Fixed
- Renamed `schema` field to `schema_version` in BuildManifest to avoid conflict with BaseModel.schema
- Fixed Pydantic warning about field name shadowing

## [0.1.4] - 2025-04-25

### Fixed
- Implemented top-level `arc version` command for better developer experience

## [0.1.3] - 2025-04-25

### Fixed
- Fixed `arc version` command in CLI to work correctly

## [0.1.2] - 2025-04-25

### Fixed
- Fixed version string in `__init__.py` to match package version
- Fixed `arc version` command in CLI

## [0.1.1] - 2025-04-25

### Added
- Added JSON output format to `arc trace file` command via the new `--format` option
- Added comprehensive documentation for the JSON output format in CLI and API docs

### Changed
- Updated documentation to include examples of using the JSON output format

## [0.1.0] - 2025-04-23

### Added
- Initial stable release of Arc Memory SDK
- Core functionality for building and querying knowledge graphs
- Support for Git, GitHub, and ADR data sources
- CLI commands for building graphs and tracing history
- Python API for programmatic access to the knowledge graph
