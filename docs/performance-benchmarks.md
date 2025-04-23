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
| Plugin Discovery | 0.095 | Discovering and registering 3 built-in plugins |
| Initial Build | 2.553 | Building the knowledge graph from scratch |
| Incremental Build | 0.473 | Updating the knowledge graph with new data |
| Trace History Query | N/A | Currently encountering errors |

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
   - Fix implementation issues causing errors
   - Optimize database queries
   - Add caching for frequently accessed data

2. **Build Process**
   - Optimize database writes
   - Parallelize plugin processing
   - Improve incremental build detection

3. **Plugin Architecture**
   - Lazy loading of plugins
   - Configuration options for disabling unused plugins

## Next Steps

1. Fix the trace history implementation to address current errors
2. Implement performance optimizations for the trace history algorithm
3. Add benchmarks for medium and large repositories
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
