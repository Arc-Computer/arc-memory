# Dependencies Guide

This guide provides a comprehensive list of dependencies for Arc Memory SDK and instructions for setting up your environment.

**Related Documentation:**
- [Installation](../index.md#installation) - Basic installation instructions
- [Test Environment Setup](./test-environment.md) - Setting up a test environment
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions

## Core Dependencies

Arc Memory SDK requires Python 3.10 or higher and depends on several libraries for its core functionality:

| Dependency | Version | Purpose |
|------------|---------|---------|
| `networkx` | ≥3.0 | Graph algorithms and data structures |
| `apsw` | ≥3.40.0 | SQLite database wrapper with advanced features |
| `pydantic` | ≥2.0.0 | Data validation and settings management |
| `zstandard` | ≥0.20.0 | Database compression |

## Feature-Specific Dependencies

Depending on which features you use, you may need additional dependencies:

### GitHub Integration

| Dependency | Version | Purpose |
|------------|---------|---------|
| `requests` | ≥2.28.0 | HTTP requests for GitHub API |
| `pyjwt` | ≥2.6.0 | JWT token handling for GitHub auth |
| `cryptography` | ≥43.0.0 | Required for PyJWT's RS256 algorithm |
| `keyring` | ≥23.13.1 | Secure credential storage |

### Command-Line Interface

| Dependency | Version | Purpose |
|------------|---------|---------|
| `typer` | ≥0.9.0 | Command-line interface |
| `rich` | ≥13.0.0 | Rich text and formatting in terminal |
| `tqdm` | ≥4.65.0 | Progress bars |

### ADR Processing

| Dependency | Version | Purpose |
|------------|---------|---------|
| `pyyaml` | ≥6.0 | YAML parsing for ADRs |
| `markdown-it-py` | ≥2.2.0 | Markdown parsing for ADRs |

### Git Integration

| Dependency | Version | Purpose |
|------------|---------|---------|
| `gitpython` | ≥3.1.30 | Git repository interaction |

## Optional Dependencies

Arc Memory SDK also has optional dependencies for specific use cases:

### Development

```bash
pip install arc-memory[dev]
```

| Dependency | Version | Purpose |
|------------|---------|---------|
| `pytest` | ≥7.3.1 | Testing framework |
| `pytest-cov` | ≥4.1.0 | Test coverage |
| `mypy` | ≥1.3.0 | Type checking |
| `black` | ≥23.3.0 | Code formatting |
| `isort` | ≥5.12.0 | Import sorting |
| `pre-commit` | ≥3.3.2 | Pre-commit hooks |
| `responses` | ≥0.23.1 | Mocking API responses in tests |

### Testing

```bash
pip install arc-memory[test]
```

| Dependency | Version | Purpose |
|------------|---------|---------|
| `pytest` | ≥7.3.1 | Testing framework |
| `pytest-cov` | ≥4.1.0 | Test coverage |
| `responses` | ≥0.23.1 | Mocking API responses in tests |

### Documentation

```bash
pip install arc-memory[docs]
```

| Dependency | Version | Purpose |
|------------|---------|---------|
| `mkdocs` | ≥1.4.0 | Documentation generator |
| `mkdocs-material` | ≥9.0.0 | Material theme for MkDocs |
| `mkdocstrings` | ≥0.20.0 | API documentation from docstrings |

### CLI Only

```bash
pip install arc-memory[cli]
```

| Dependency | Version | Purpose |
|------------|---------|---------|
| `typer` | ≥0.9.0 | Command-line interface |
| `rich` | ≥13.0.0 | Rich text and formatting in terminal |
| `tqdm` | ≥4.65.0 | Progress bars |
| `keyring` | ≥23.13.1 | Secure credential storage |

## Installation

### Basic Installation

```bash
pip install arc-memory
```

This installs Arc Memory SDK with all core dependencies.

### Installation with Optional Dependencies

```bash
# Install with development dependencies
pip install arc-memory[dev]

# Install with testing dependencies
pip install arc-memory[test]

# Install with documentation dependencies
pip install arc-memory[docs]

# Install with CLI dependencies only
pip install arc-memory[cli]

# Install with multiple optional dependency groups
pip install arc-memory[test,docs]
```

## Dependency Verification

Arc Memory SDK includes a built-in dependency checker that verifies all required dependencies are installed. You can run it manually:

```python
from arc_memory.dependencies import validate_dependencies

# Check core dependencies only
validate_dependencies(include_optional=False)

# Check all dependencies including optional ones
validate_dependencies(include_optional=True)
```

If any dependencies are missing, the function will raise a `DependencyError` with details about the missing dependencies and instructions for installing them.

## System Requirements

- **Python**: 3.10 or higher
- **Operating Systems**: Linux, macOS, Windows
- **Disk Space**: At least 100MB for the SDK and dependencies, plus space for the knowledge graph (varies by repository size)
- **Memory**: At least 512MB of RAM, 1GB recommended for larger repositories

## Next Steps

- [Set up a test environment](./test-environment.md)
- [Learn about common errors and solutions](./troubleshooting.md)
- [Start building your knowledge graph](../examples/building-graphs.md)
