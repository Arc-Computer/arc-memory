#!/usr/bin/env python3
"""
Cross-Repository Explorer

This script demonstrates Arc Memory's multi-repository capabilities by analyzing
relationships and dependencies across repository boundaries.

Usage:
    python cross_repo_explorer.py --repos /path/to/repo1 /path/to/repo2 [--names "Name1" "Name2"] [--analysis TYPE]

Example:
    python cross_repo_explorer.py --repos ./frontend ./backend --names "Frontend" "Backend" --analysis dependencies
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import Arc Memory SDK
try:
    from arc_memory.sdk import Arc
except ImportError:
    print("Error: Arc Memory SDK not found. Please install it with 'pip install arc-memory'.")
    sys.exit(1)

# Import analyzers
try:
    from analyzers.dependency_analyzer import analyze_dependencies
    from analyzers.decision_analyzer import analyze_decisions
    from analyzers.component_analyzer import analyze_components
except ImportError:
    # Try relative import (when imported as a module)
    try:
        from .analyzers.dependency_analyzer import analyze_dependencies
        from .analyzers.decision_analyzer import analyze_decisions
        from .analyzers.component_analyzer import analyze_components
    except ImportError:
        print("Error: Could not import analyzer modules.")
        print("Make sure you're running this script from the correct directory.")
        sys.exit(1)


class CrossRepoExplorer:
    """Cross-Repository Explorer class."""

    def __init__(self):
        """Initialize the Cross-Repository Explorer."""
        self.arc = None
        self.repositories = []
        self.repo_ids = []
        self.repo_names = {}

    def initialize(self) -> bool:
        """Initialize Arc Memory.

        Returns:
            True if initialization was successful, False otherwise
        """
        print("\n=== Initializing Cross-Repository Explorer ===\n")

        try:
            # Initialize Arc Memory with the first repository
            print("Connecting to Arc Memory...")
            self.arc = Arc()
            print("Successfully connected to Arc Memory.")
            return True
        except Exception as e:
            print(f"Error initializing Arc Memory: {e}")
            return False

    def add_repositories(self, repo_paths: List[str], repo_names: Optional[List[str]] = None) -> bool:
        """Add repositories to the knowledge graph.

        Args:
            repo_paths: List of repository paths
            repo_names: Optional list of repository names

        Returns:
            True if repositories were added successfully, False otherwise
        """
        print("\n=== Adding Repositories ===\n")

        if not self.arc:
            print("Error: Arc Memory not initialized.")
            return False

        if not repo_paths:
            print("Error: No repository paths provided.")
            return False

        # Use provided names or generate default names
        names = repo_names if repo_names else [f"Repository {i+1}" for i in range(len(repo_paths))]

        # Ensure we have the same number of names as paths
        if len(names) < len(repo_paths):
            names.extend([f"Repository {i+1}" for i in range(len(names), len(repo_paths))])

        try:
            # Add each repository
            for i, (repo_path, repo_name) in enumerate(zip(repo_paths, names)):
                print(f"Adding repository: {repo_name} ({repo_path})")

                # Check if repository exists
                repo_path = os.path.abspath(repo_path)
                if not os.path.exists(repo_path):
                    error_message = f"Error: Repository path does not exist: {repo_path}"
                    print(error_message)
                    return False

                # Add repository to Arc Memory
                try:
                    repo_id = self.arc.add_repository(repo_path, name=repo_name)
                    self.repositories.append(repo_path)
                    self.repo_ids.append(repo_id)
                    self.repo_names[repo_id] = repo_name
                    print(f"Successfully added repository: {repo_name} (ID: {repo_id})")
                except Exception as e:
                    print(f"Error adding repository {repo_name}: {e}")

                    # Try to find the repository if it already exists
                    try:
                        repos = self.arc.list_repositories()
                        for repo in repos:
                            if os.path.abspath(repo["local_path"]) == repo_path:
                                repo_id = repo["id"]
                                self.repositories.append(repo_path)
                                self.repo_ids.append(repo_id)
                                self.repo_names[repo_id] = repo_name
                                print(f"Repository already exists: {repo_name} (ID: {repo_id})")
                                break
                    except Exception as e2:
                        print(f"Error finding existing repository: {e2}")

            # Set active repositories
            if self.repo_ids:
                self.arc.set_active_repositories(self.repo_ids)
                print(f"\nSet {len(self.repo_ids)} active repositories for analysis.")
                return True
            else:
                print("Error: No repositories were added successfully.")
                return False
        except Exception as e:
            print(f"Error adding repositories: {e}")
            return False

    def build_knowledge_graphs(self) -> bool:
        """Build knowledge graphs for all repositories.

        Returns:
            True if knowledge graphs were built successfully, False otherwise
        """
        print("\n=== Building Knowledge Graphs ===\n")

        if not self.arc or not self.repo_ids:
            print("Error: No repositories added.")
            return False

        try:
            for repo_id in self.repo_ids:
                repo_name = self.repo_names.get(repo_id, repo_id)
                print(f"Building knowledge graph for {repo_name}...")

                try:
                    # Check if the knowledge graph already exists
                    # This is a simple check to avoid rebuilding existing graphs
                    cursor = self.arc.adapter.conn.execute(
                        "SELECT COUNT(*) FROM nodes WHERE repo_id = ?",
                        (repo_id,)
                    )
                    count = cursor.fetchone()[0]

                    if count > 0:
                        print(f"Knowledge graph for {repo_name} already exists with {count} nodes.")
                        print("Skipping build. Use --force to rebuild.")
                        continue

                    # Build the knowledge graph
                    result = self.arc.build_repository(
                        repo_id=repo_id,
                        include_github=True,
                        include_architecture=True,
                        verbose=True
                    )

                    print(f"Successfully built knowledge graph for {repo_name}.")
                    print(f"Added {result.get('nodes_added', 0)} nodes and {result.get('edges_added', 0)} edges.")
                except Exception as e:
                    print(f"Error building knowledge graph for {repo_name}: {e}")

            return True
        except Exception as e:
            print(f"Error building knowledge graphs: {e}")
            return False

    def run_analysis(self, analysis_type: str = "all") -> bool:
        """Run the specified analysis.

        Args:
            analysis_type: Type of analysis to run (dependencies, decisions, components, or all)

        Returns:
            True if analysis was successful, False otherwise
        """
        if not self.arc or not self.repo_ids:
            print("Error: No repositories added.")
            return False

        try:
            # Run the specified analysis
            if analysis_type in ["dependencies", "all"]:
                print("\n=== Cross-Repository Dependencies ===\n")
                analyze_dependencies(self.arc, self.repo_ids, self.repo_names)

            if analysis_type in ["decisions", "all"]:
                print("\n=== Cross-Repository Decisions ===\n")
                analyze_decisions(self.arc, self.repo_ids, self.repo_names)

            if analysis_type in ["components", "all"]:
                print("\n=== Shared Components ===\n")
                analyze_components(self.arc, self.repo_ids, self.repo_names)

            return True
        except Exception as e:
            print(f"Error running analysis: {e}")
            return False

    def run(self, repo_paths: List[str], repo_names: Optional[List[str]] = None, analysis_type: str = "all") -> bool:
        """Run the Cross-Repository Explorer.

        Args:
            repo_paths: List of repository paths
            repo_names: Optional list of repository names
            analysis_type: Type of analysis to run

        Returns:
            True if the explorer ran successfully, False otherwise
        """
        # Initialize Arc Memory
        if not self.initialize():
            return False

        # Add repositories
        if not self.add_repositories(repo_paths, repo_names):
            return False

        # Build knowledge graphs
        if not self.build_knowledge_graphs():
            return False

        # Run analysis
        if not self.run_analysis(analysis_type):
            return False

        print("\n=== Cross-Repository Explorer Complete ===\n")
        return True


def main():
    """Main entry point for the Cross-Repository Explorer."""
    parser = argparse.ArgumentParser(description="Cross-Repository Explorer")
    parser.add_argument("--repos", type=str, nargs="+", required=True, help="Paths to the repositories")
    parser.add_argument("--names", type=str, nargs="+", help="Names for the repositories")
    parser.add_argument("--analysis", type=str, default="all", choices=["dependencies", "decisions", "components", "all"], help="Type of analysis to run")
    parser.add_argument("--force", action="store_true", help="Force rebuild of knowledge graphs")
    args = parser.parse_args()

    # Create and run the Cross-Repository Explorer
    explorer = CrossRepoExplorer()
    success = explorer.run(args.repos, args.names, args.analysis)

    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
