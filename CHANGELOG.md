# Changelog

All notable changes to the Arc Memory SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [0.1.5] - 2024-04-25

### Fixed
- Renamed `schema` field to `schema_version` in BuildManifest to avoid conflict with BaseModel.schema
- Fixed Pydantic warning about field name shadowing

## [0.1.4] - 2024-04-25

### Fixed
- Implemented top-level `arc version` command for better developer experience

## [0.1.3] - 2024-04-25

### Fixed
- Fixed `arc version` command in CLI to work correctly

## [0.1.2] - 2024-04-25

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
