# Performance Benchmarks

This document provides performance benchmarks for Arc Memory, focusing on key operations that impact user experience.

## Benchmark Methodology

We use a custom benchmarking script located in `tests/benchmark/benchmark.py` to measure the performance of key operations:

1. **Plugin Discovery**: Time to discover and register all plugins
2. **Initial Build**: Time to build the knowledge graph from scratch
3. **Incremental Build**: Time to update the knowledge graph with new data
4. **Trace History Query**: Time to trace the history of a specific line

Benchmarks are run on repositories of different sizes:
- **Small**: Arc Memory repository (~100 commits)
- **Medium**: Flask repository (~5,000 commits)
- **Large**: Django repository (~30,000 commits)

## Current Performance (as of April 2025)

### Small Repository (Arc Memory)

| Operation | Duration (seconds) | Notes |
|-----------|-------------------|-------|
| Plugin Discovery | 0.100 | Discovering and registering 3 built-in plugins |
| Initial Build | 3.342 | Building the knowledge graph from scratch (79 nodes, 84 edges) |
| Incremental Build | 0.446 | Updating the knowledge graph with new data |
| Trace History Query | 0.000109 | Tracing history for a specific line (109 microseconds) |

### Performance Targets

Based on the PRD and user experience requirements:

| Operation | Target Duration | Rationale |
|-----------|----------------|-----------|
| Plugin Discovery | < 0.5 seconds | Fast startup time for CLI and VS Code extension |
| Initial Build | < 30 seconds | Acceptable one-time cost for new users |
| Incremental Build | < 5 seconds | Fast enough for CI integration |
| Trace History Query | < 200ms | Required for responsive VS Code extension |

## Performance Optimization Opportunities

Based on the current benchmarks, we've identified the following optimization opportunities:

1. **Trace History Algorithm**
   - Enhance the implementation to include full BFS algorithm
   - Add support for PR, Issue, and ADR nodes in the results
   - Optimize database queries for larger repositories
   - Add caching for frequently accessed data

2. **Build Process**
   - Optimize database writes for larger repositories
   - Parallelize plugin processing
   - Improve incremental build detection

3. **Plugin Architecture**
   - Lazy loading of plugins
   - Configuration options for disabling unused plugins

## Recent Improvements

1. **Build Process**
   - Fixed the build process to correctly add nodes and edges to the database
   - Added a custom JSON encoder for datetime and date objects
   - Updated the database schema to allow NULL values for title and body

2. **ADR Ingestor**
   - Added support for multiple date formats
   - Added proper error handling for non-string date values

3. **Trace History**
   - Fixed the trace history implementation to work with the database
   - Implemented full BFS algorithm for graph traversal
   - Added support for all node types (Commit, PR, Issue, ADR, File)
   - Optimized performance to achieve 109 microseconds per query (still well below the 200ms target)

## Next Steps

1. Add benchmarks for medium and large repositories
2. Add more comprehensive tests for the trace history algorithm
3. Optimize database queries for larger repositories
4. Continuously monitor performance as new features are added

## Running Benchmarks

To run the benchmarks yourself:

```bash
# Install the package in development mode
pip install -e .

# Run benchmarks on a small repository
python tests/benchmark/benchmark.py --repo-size small --output benchmark_results_small.json

# Run benchmarks on a medium repository
python tests/benchmark/benchmark.py --repo-size medium --output benchmark_results_medium.json

# Run benchmarks on a large repository
python tests/benchmark/benchmark.py --repo-size large --output benchmark_results_large.json
```

The benchmark results will be saved to the specified output file in JSON format.
