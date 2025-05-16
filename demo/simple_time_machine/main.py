#!/usr/bin/env python3
"""
Simple Code Time Machine Demo

This script demonstrates Arc Memory's temporal understanding capabilities in a simple,
easy-to-understand way with minimal dependencies.

Usage:
    python main.py [--repo PATH] [--file PATH] [--interactive]

Example:
    python main.py --repo ./ --file arc_memory/sdk/core.py
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

# Import visualizers
try:
    from visualize_timeline import visualize_timeline
    from visualize_decisions import visualize_decisions
    from visualize_impact import visualize_impact
    from utils import print_header, print_section
except ImportError:
    # Try relative import (when imported as a module)
    try:
        from .visualize_timeline import visualize_timeline
        from .visualize_decisions import visualize_decisions
        from .visualize_impact import visualize_impact
        from .utils import print_header, print_section
    except ImportError:
        print("Error: Could not import visualization modules.")
        sys.exit(1)


class SimpleCodeTimeMachine:
    """Simple Code Time Machine demo class."""

    def __init__(self, repo_path: str = "./", interactive: bool = False):
        """Initialize the Simple Code Time Machine.

        Args:
            repo_path: Path to the repository
            interactive: Whether to run in interactive mode
        """
        self.repo_path = repo_path
        self.interactive = interactive
        self.arc = None
        self.file_path = None

    def initialize(self) -> bool:
        """Initialize Arc Memory and check if the knowledge graph exists.

        Returns:
            True if initialization was successful, False otherwise
        """
        print_header("Initializing Simple Code Time Machine")

        try:
            # Initialize Arc Memory
            print("Connecting to Arc Memory knowledge graph...")
            self.arc = Arc(repo_path=self.repo_path)
            print("Successfully connected to knowledge graph.")
            return True
        except Exception as e:
            print(f"Error initializing: {e}")
            return False

    def select_file(self, file_path: Optional[str] = None) -> Optional[str]:
        """Select a file to explore.

        Args:
            file_path: Optional file path to use

        Returns:
            The selected file path or None if selection failed
        """
        if file_path:
            self.file_path = file_path
            print(f"Selected file: {self.file_path}")
            return self.file_path

        if not self.interactive:
            print("No file specified and not in interactive mode.")
            return None

        # In interactive mode, let the user select a file
        print("Please enter a file path to explore:")
        self.file_path = input("> ")

        # Check if the file exists
        if not os.path.exists(os.path.join(self.repo_path, self.file_path)):
            print(f"File not found: {self.file_path}")
            return None

        print(f"Selected file: {self.file_path}")
        return self.file_path

    def explore_timeline(self) -> bool:
        """Explore the timeline of the selected file.

        Returns:
            True if exploration was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        print_section(f"Timeline Exploration: {self.file_path}")

        try:
            # Get file history using Arc Memory SDK
            print("Retrieving file history...")
            entity_id = f"file:{self.file_path}"
            try:
                history = self.arc.get_entity_history(entity_id=entity_id, include_related=True)
                if not history:
                    print(f"Warning: No history found for {entity_id}")
                    # Try to get related entities instead
                    print(f"Trying to get related entities instead...")
                    related = self.arc.get_related_entities(
                        entity_id=entity_id,
                        max_results=10
                    )
                    history = related  # Use related entities as a fallback
            except Exception as e:
                print(f"Error retrieving file history: {e}")
                history = []

            # Visualize the timeline
            visualize_timeline(history, self.file_path)
            return True

        except Exception as e:
            print(f"Error exploring timeline: {e}")
            return False

    def explore_decisions(self) -> bool:
        """Explore key decisions that shaped the selected file.

        Returns:
            True if exploration was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        print_section(f"Decision Archaeology: {self.file_path}")

        try:
            # For demo purposes, we'll analyze a few key lines in the file
            file_path = os.path.join(self.repo_path, self.file_path)

            # Get the total number of lines in the file
            with open(file_path, 'r') as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Select a few lines to analyze (e.g., every 20% of the file)
            line_numbers = [
                max(1, int(total_lines * 0.2)),
                max(1, int(total_lines * 0.5)),
                max(1, int(total_lines * 0.8))
            ]

            decision_trails = []

            for line_number in line_numbers:
                print(f"Analyzing line {line_number}...")

                # Get decision trail using Arc Memory SDK
                trail = self.arc.get_decision_trail(
                    file_path=self.file_path,
                    line_number=line_number,
                    max_results=3,
                    include_rationale=True
                )

                if trail:
                    decision_trails.append((line_number, trail))

            # Visualize the decisions
            visualize_decisions(decision_trails, self.file_path)
            return True

        except Exception as e:
            print(f"Error exploring decisions: {e}")
            return False

    def predict_impact(self) -> bool:
        """Predict the impact of changes to the selected file.

        Returns:
            True if prediction was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        print_section(f"Impact Prediction: {self.file_path}")

        try:
            print("Analyzing potential impact...")

            # Get impact analysis using Arc Memory SDK
            component_id = f"file:{self.file_path}"
            try:
                impact = self.arc.analyze_component_impact(
                    component_id=component_id,
                    impact_types=["direct", "indirect"],
                    max_depth=3
                )
            except Exception as e:
                print(f"Warning: Could not analyze component impact: {e}")
                # Try to get related entities instead
                try:
                    print(f"Trying to get related entities instead...")
                    related = self.arc.get_related_entities(
                        entity_id=component_id,
                        max_results=10
                    )
                    impact = related  # Use related entities as a fallback
                except Exception as e2:
                    print(f"Error getting related entities: {e2}")
                    impact = []

            # Visualize the impact
            visualize_impact(impact, self.file_path)
            return True

        except Exception as e:
            print(f"Error predicting impact: {e}")
            return False

    def run(self, file_path: Optional[str] = None) -> bool:
        """Run the Simple Code Time Machine demo.

        Args:
            file_path: Optional file path to explore

        Returns:
            True if the demo ran successfully, False otherwise
        """
        # Initialize Arc Memory
        if not self.initialize():
            return False

        # Select a file to explore
        if not self.select_file(file_path):
            return False

        # Explore the timeline
        self.explore_timeline()

        # Explore key decisions
        self.explore_decisions()

        # Predict impact
        self.predict_impact()

        print_header("Demo Complete")
        print("Thank you for using the Simple Code Time Machine!")
        return True


def main():
    """Main entry point for the Simple Code Time Machine demo."""
    parser = argparse.ArgumentParser(description="Simple Code Time Machine Demo")
    parser.add_argument("--repo", type=str, default="./", help="Path to the repository")
    parser.add_argument("--file", type=str, help="Path to the file to explore")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    args = parser.parse_args()

    # Create and run the Simple Code Time Machine
    demo = SimpleCodeTimeMachine(repo_path=args.repo, interactive=args.interactive)
    success = demo.run(file_path=args.file)

    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
