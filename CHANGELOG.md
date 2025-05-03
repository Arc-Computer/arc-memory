# Changelog

All notable changes to the Arc Memory SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
