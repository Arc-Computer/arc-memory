#!/bin/bash

# This script runs the GitHub ingestion benchmarks for repositories of different sizes.
# It requires a GitHub token to be set in the GITHUB_TOKEN environment variable.

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is not set."
    echo "Please set it to a valid GitHub token with appropriate permissions."
    exit 1
fi

# Create output directory
mkdir -p benchmarks

# Run benchmarks for small repository
echo "Running benchmarks for small repository (Arc Memory)..."
python tests/benchmark/benchmark.py --repo-size small --output benchmarks/benchmark_results_small_github.json --github-token $GITHUB_TOKEN

# Run benchmarks for medium repository
echo "Running benchmarks for medium repository (Flask)..."
python tests/benchmark/benchmark.py --repo-size medium --output benchmarks/benchmark_results_medium_github.json --github-token $GITHUB_TOKEN

# Run benchmarks for large repository
echo "Running benchmarks for large repository (Django)..."
python tests/benchmark/benchmark.py --repo-size large --output benchmarks/benchmark_results_large_github.json --github-token $GITHUB_TOKEN

echo "All benchmarks completed. Results are in the benchmarks/ directory."
