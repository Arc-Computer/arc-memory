"""Benchmark script for Arc Memory performance testing."""

import argparse
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import git
from git import Repo

from arc_memory.plugins import discover_plugins
from arc_memory.sql.db import ensure_arc_dir, get_connection
from arc_memory.trace import trace_history
from tests.benchmark.build_helper import build_graph

# Constants
SMALL_REPO_URL = "https://github.com/Arc-Computer/arc-memory.git"
MEDIUM_REPO_URL = "https://github.com/pallets/flask.git"
LARGE_REPO_URL = "https://github.com/django/django.git"

# Benchmark results
results = {
    "timestamp": datetime.now().isoformat(),
    "system_info": {
        "os": os.uname().sysname,
        "machine": os.uname().machine,
        "python_version": os.sys.version,
    },
    "benchmarks": [],
}


def clone_repo(url: str, target_dir: Path) -> git.Repo:
    """Clone a repository for benchmarking.

    Args:
        url: The URL of the repository to clone.
        target_dir: The directory to clone the repository to.

    Returns:
        The cloned repository.
    """
    print(f"Cloning {url} to {target_dir}...")
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    return Repo.clone_from(url, target_dir)


def benchmark_build(repo_path: Path, incremental: bool = False) -> Dict:
    """Benchmark the build process.

    Args:
        repo_path: The path to the repository.
        incremental: Whether to perform an incremental build.

    Returns:
        A dictionary of benchmark results.
    """
    # Clear the .arc directory
    arc_dir = ensure_arc_dir()
    if not incremental:
        for file in arc_dir.glob("*"):
            if file.is_file():
                file.unlink()

    # Measure build time
    start_time = time.time()
    node_count, edge_count, plugin_metadata = build_graph(
        repo_path=repo_path,
        output_path=arc_dir / "graph.db",
        incremental=incremental,
    )
    end_time = time.time()

    # Get database size
    db_path = arc_dir / "graph.db"
    db_size = db_path.stat().st_size if db_path.exists() else 0

    # Get node and edge counts
    node_count = 0
    edge_count = 0
    if db_path.exists():
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes")
        node_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM edges")
        edge_count = cursor.fetchone()[0]
        conn.close()

    return {
        "type": "build",
        "incremental": incremental,
        "duration_seconds": end_time - start_time,
        "db_size_bytes": db_size,
        "node_count": node_count,
        "edge_count": edge_count,
    }


def benchmark_trace(repo_path: Path, file_path: str, line_number: int, iterations: int = 10) -> Dict:
    """Benchmark the trace history algorithm.

    Args:
        repo_path: The path to the repository.
        file_path: The path to the file to trace.
        line_number: The line number to trace.
        iterations: The number of iterations to run.

    Returns:
        A dictionary of benchmark results.
    """
    # Ensure the database exists
    arc_dir = ensure_arc_dir()
    db_path = arc_dir / "graph.db"
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    # Get connection
    conn = get_connection(db_path)

    # Warm up
    try:
        trace_history(conn, file_path, line_number)
    except Exception as e:
        print(f"Error in warm-up: {e}")

    # Measure trace time
    durations = []
    result_count = 0
    for _ in range(iterations):
        try:
            start_time = time.time()
            result = trace_history(conn, file_path, line_number)
            end_time = time.time()
            durations.append(end_time - start_time)
            result_count = len(result) if result else 0
        except Exception as e:
            print(f"Error in trace_history: {e}")
            durations.append(0.0)

    conn.close()

    # Handle the case where all iterations failed
    if not durations or all(d == 0.0 for d in durations):
        return {
            "type": "trace",
            "file_path": file_path,
            "line_number": line_number,
            "iterations": iterations,
            "durations_seconds": durations,
            "avg_duration_seconds": 0.0,
            "min_duration_seconds": 0.0,
            "max_duration_seconds": 0.0,
            "result_count": 0,
            "error": "All iterations failed"
        }

    # Filter out failed iterations
    valid_durations = [d for d in durations if d > 0.0]

    return {
        "type": "trace",
        "file_path": file_path,
        "line_number": line_number,
        "iterations": iterations,
        "durations_seconds": durations,
        "avg_duration_seconds": sum(valid_durations) / len(valid_durations) if valid_durations else 0.0,
        "min_duration_seconds": min(valid_durations) if valid_durations else 0.0,
        "max_duration_seconds": max(valid_durations) if valid_durations else 0.0,
        "result_count": result_count,
        "failed_iterations": iterations - len(valid_durations)
    }


def benchmark_plugins() -> Dict:
    """Benchmark the plugin discovery process.

    Returns:
        A dictionary of benchmark results.
    """
    start_time = time.time()
    registry = discover_plugins()
    end_time = time.time()

    return {
        "type": "plugins",
        "duration_seconds": end_time - start_time,
        "plugin_count": len(registry.list_plugins()),
        "plugins": registry.list_plugins(),
    }


def run_benchmarks(repo_size: str, output_file: Optional[Path] = None) -> None:
    """Run all benchmarks.

    Args:
        repo_size: The size of the repository to benchmark (small, medium, large).
        output_file: The file to write the results to.
    """
    # Select repository URL based on size
    if repo_size == "small":
        repo_url = SMALL_REPO_URL
    elif repo_size == "medium":
        repo_url = MEDIUM_REPO_URL
    elif repo_size == "large":
        repo_url = LARGE_REPO_URL
    else:
        raise ValueError(f"Invalid repository size: {repo_size}")

    # Create temporary directory for the repository
    temp_dir = Path.home() / ".arc" / "benchmark" / repo_size

    try:
        # Clone repository
        repo = clone_repo(repo_url, temp_dir)

        # Benchmark plugin discovery
        print("Benchmarking plugin discovery...")
        plugin_results = benchmark_plugins()
        results["benchmarks"].append(plugin_results)

        # Benchmark initial build
        print("Benchmarking initial build...")
        build_results = benchmark_build(temp_dir, incremental=False)
        results["benchmarks"].append(build_results)

        # Benchmark incremental build
        print("Benchmarking incremental build...")
        incremental_results = benchmark_build(temp_dir, incremental=True)
        results["benchmarks"].append(incremental_results)

        # Find a file to trace
        print("Finding a file to trace...")

        # First try to find README.md which should exist in most repositories
        if (temp_dir / "README.md").exists():
            file_to_trace = "README.md"
        elif (temp_dir / "README.rst").exists():
            file_to_trace = "README.rst"
        else:
            # Fallback to searching for any Python file
            python_files = list(temp_dir.glob("**/*.py"))
            if python_files:
                file_to_trace = str(python_files[0].relative_to(temp_dir))
            else:
                # Last resort - use any file
                all_files = list(temp_dir.glob("**/*.*"))
                if all_files:
                    file_to_trace = str(all_files[0].relative_to(temp_dir))
                else:
                    print("No files found in the repository.")
                    file_to_trace = ""

        # Verify the file exists
        if not (temp_dir / file_to_trace).exists():
            print(f"File {file_to_trace} not found. Skipping trace history benchmark.")
            trace_results = {
                "type": "trace",
                "file_path": file_to_trace,
                "line_number": 1,
                "iterations": 0,
                "durations_seconds": [],
                "avg_duration_seconds": 0.0,
                "min_duration_seconds": 0.0,
                "max_duration_seconds": 0.0,
                "result_count": 0,
                "error": "File not found"
            }
        else:
            # Benchmark trace history
            print(f"Benchmarking trace history for {file_to_trace}:1...")
            trace_results = benchmark_trace(temp_dir, file_to_trace, 1)
        results["benchmarks"].append(trace_results)

        # Print summary
        print("\nBenchmark Summary:")
        print(f"Plugin Discovery: {plugin_results['duration_seconds']:.3f} seconds")
        print(f"Initial Build: {build_results['duration_seconds']:.3f} seconds")
        print(f"Incremental Build: {incremental_results['duration_seconds']:.3f} seconds")
        print(f"Trace History: {trace_results['avg_duration_seconds']:.3f} seconds (avg)")

        # Write results to file
        if output_file:
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"Results written to {output_file}")

    finally:
        # Clean up
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Arc Memory performance.")
    parser.add_argument(
        "--repo-size",
        choices=["small", "medium", "large"],
        default="small",
        help="Size of the repository to benchmark.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="File to write benchmark results to.",
    )

    args = parser.parse_args()
    run_benchmarks(args.repo_size, args.output)
