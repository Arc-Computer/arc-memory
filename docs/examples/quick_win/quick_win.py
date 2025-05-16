#!/usr/bin/env python3
"""
Arc Memory Quick Win Demo

A 5-minute demo that shows the immediate value of Arc Memory with minimal setup.

Usage:
    python quick_win.py [--file PATH] [--depth DEPTH] [--focus FOCUS]

Example:
    python quick_win.py --file src/core/auth.py --depth 3 --focus decisions
"""

import argparse
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import Arc Memory SDK
try:
    from arc_memory.sdk import Arc
except ImportError:
    print("Error: Arc Memory SDK not found. Please install it with 'pip install arc-memory'.")
    sys.exit(1)


class QuickWinDemo:
    """Quick Win Demo for Arc Memory."""

    def __init__(self):
        """Initialize the Quick Win Demo."""
        self.arc = None
        self.file_path = None
        self.depth = 2
        self.focus = "all"

    def initialize(self) -> bool:
        """Initialize Arc Memory and check if the knowledge graph exists.

        Returns:
            True if initialization was successful, False otherwise
        """
        print("\n=== Arc Memory Quick Win Demo ===\n")

        try:
            # Initialize Arc Memory
            print("Connecting to Arc Memory knowledge graph...")
            self.arc = Arc()
            print("Successfully connected to knowledge graph.")
            return True
        except Exception as e:
            print(f"Error initializing: {e}")
            return False

    def find_interesting_file(self, specified_file: Optional[str] = None) -> Optional[str]:
        """Find an interesting file to analyze.

        Args:
            specified_file: Optional file path specified by the user

        Returns:
            The path to an interesting file or None if no file was found
        """
        if specified_file:
            self.file_path = specified_file
            print(f"Using specified file: {self.file_path}")
            return self.file_path

        print("Finding an interesting file to analyze...")

        try:
            # Get all file nodes
            cursor = self.arc.adapter.conn.execute(
                """
                SELECT id, title
                FROM nodes
                WHERE type = 'file'
                """
            )
            files = cursor.fetchall()

            if not files:
                print("No files found in the knowledge graph.")
                return None

            # Find files with the most connections
            interesting_files = []
            for file in files:
                file_id = file["id"]
                
                # Count connections
                cursor = self.arc.adapter.conn.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM edges
                    WHERE src = ? OR dst = ?
                    """,
                    (file_id, file_id)
                )
                count = cursor.fetchone()["count"]
                
                interesting_files.append({
                    "id": file_id,
                    "path": file_id.replace("file:", ""),
                    "connections": count
                })

            # Sort by number of connections
            interesting_files.sort(key=lambda x: x["connections"], reverse=True)
            
            # Select one of the top 10 files
            selected = random.choice(interesting_files[:10])
            self.file_path = selected["path"]
            
            print(f"Selected file: {self.file_path}")
            print(f"This file has {selected['connections']} connections in the knowledge graph.")
            
            return self.file_path

        except Exception as e:
            print(f"Error finding interesting file: {e}")
            return None

    def analyze_file_history(self) -> bool:
        """Analyze the history of the selected file.

        Returns:
            True if analysis was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        if self.focus not in ["all", "history"]:
            return True

        print("\n=== File History ===\n")

        try:
            # Get file history
            entity_id = f"file:{self.file_path}"
            history = self.arc.get_entity_history(
                entity_id=entity_id,
                include_related=True
            )

            if not history:
                print("No history found for this file.")
                return False

            # Sort history by timestamp
            sorted_history = sorted(
                history,
                key=lambda x: getattr(x, "timestamp", ""),
                reverse=False
            )

            # Display key events
            for i, event in enumerate(sorted_history):
                # Get event properties
                timestamp = getattr(event, "timestamp", "Unknown date")
                if hasattr(timestamp, "strftime"):
                    timestamp = timestamp.strftime("%Y-%m-%d")
                
                event_type = getattr(event, "type", "event")
                
                # Get author
                author = "Unknown"
                if hasattr(event, "author"):
                    author = event.author
                elif hasattr(event, "user"):
                    author = event.user
                
                # Get message/title
                message = ""
                if hasattr(event, "message"):
                    message = event.message
                elif hasattr(event, "title"):
                    message = event.title
                
                # Display event
                print(f"- {event_type.capitalize()} on {timestamp} by {author}")
                if message:
                    print(f"  {message}")

            return True

        except Exception as e:
            print(f"Error analyzing file history: {e}")
            return False

    def analyze_dependencies(self) -> bool:
        """Analyze the dependencies of the selected file.

        Returns:
            True if analysis was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        if self.focus not in ["all", "dependencies"]:
            return True

        print("\n=== Key Dependencies ===\n")

        try:
            # Get related entities
            entity_id = f"file:{self.file_path}"
            related = self.arc.get_related_entities(
                entity_id=entity_id,
                max_results=10 * self.depth
            )

            if not related:
                print("No dependencies found for this file.")
                return False

            # Group by relationship type
            dependencies = []
            dependents = []
            
            for entity in related:
                # Skip non-file entities
                if not hasattr(entity, "id") or not entity.id.startswith("file:"):
                    continue
                
                # Get relationship type
                rel_type = getattr(entity, "relationship", "")
                
                # Determine if dependency or dependent
                if rel_type in ["imports", "calls", "uses", "depends_on"]:
                    dependencies.append(entity)
                elif rel_type in ["imported_by", "called_by", "used_by", "depended_on_by"]:
                    dependents.append(entity)

            # Display dependencies
            if dependencies:
                print("This file depends on:")
                for dep in dependencies[:5]:
                    path = dep.id.replace("file:", "")
                    rel = getattr(dep, "relationship", "")
                    print(f"- {path} ({rel})")
                
                if len(dependencies) > 5:
                    print(f"... and {len(dependencies) - 5} more dependencies")
            else:
                print("This file has no dependencies.")

            # Display dependents
            if dependents:
                print("\nThis file is used by:")
                for dep in dependents[:5]:
                    path = dep.id.replace("file:", "")
                    rel = getattr(dep, "relationship", "")
                    print(f"- {path} ({rel})")
                
                if len(dependents) > 5:
                    print(f"... and {len(dependents) - 5} more dependents")
            else:
                print("\nThis file is not used by other files.")

            return True

        except Exception as e:
            print(f"Error analyzing dependencies: {e}")
            return False

    def analyze_decisions(self) -> bool:
        """Analyze the decisions that shaped the selected file.

        Returns:
            True if analysis was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        if self.focus not in ["all", "decisions"]:
            return True

        print("\n=== Important Decisions ===\n")

        try:
            # Get file content to determine line count
            file_path = os.path.join(os.getcwd(), self.file_path)
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return False

            # Count lines in the file
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            line_count = len(lines)
            
            # Select a few lines to analyze
            line_numbers = []
            if line_count <= 10:
                line_numbers = [1]
            elif line_count <= 50:
                line_numbers = [int(line_count * 0.5)]
            else:
                line_numbers = [
                    int(line_count * 0.25),
                    int(line_count * 0.75)
                ]

            # Get decision trails for selected lines
            decisions = []
            for line_number in line_numbers:
                trail = self.arc.get_decision_trail(
                    file_path=self.file_path,
                    line_number=line_number,
                    max_results=5,
                    include_rationale=True
                )
                
                if trail:
                    decisions.extend(trail)

            # If no decisions found from lines, try getting related PRs
            if not decisions:
                entity_id = f"file:{self.file_path}"
                related = self.arc.get_related_entities(
                    entity_id=entity_id,
                    max_results=10 * self.depth
                )
                
                for entity in related:
                    if hasattr(entity, "type") and entity.type in ["pr", "pull_request", "issue"]:
                        decisions.append(entity)

            # Display decisions
            if not decisions:
                print("No important decisions found for this file.")
                return False

            # Display unique decisions
            seen_ids = set()
            for decision in decisions:
                # Skip if we've already seen this decision
                if hasattr(decision, "id") and decision.id in seen_ids:
                    continue
                
                if hasattr(decision, "id"):
                    seen_ids.add(decision.id)
                
                # Get decision properties
                title = getattr(decision, "title", "Unknown decision")
                
                # Get PR number if available
                pr_number = ""
                if hasattr(decision, "number"):
                    pr_number = f"(PR #{decision.number})"
                
                # Get rationale if available
                rationale = ""
                if hasattr(decision, "rationale"):
                    rationale = decision.rationale
                elif hasattr(decision, "body"):
                    rationale = decision.body
                
                # Display decision
                print(f"- {title} {pr_number}")
                if rationale:
                    # Truncate long rationales
                    if len(rationale) > 100:
                        rationale = rationale[:97] + "..."
                    print(f"  {rationale}")

            return True

        except Exception as e:
            print(f"Error analyzing decisions: {e}")
            return False

    def visualize_relationships(self) -> bool:
        """Visualize the relationships of the selected file.

        Returns:
            True if visualization was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        print("\n=== Relationship Visualization ===\n")

        try:
            # Get related entities
            entity_id = f"file:{self.file_path}"
            related = self.arc.get_related_entities(
                entity_id=entity_id,
                max_results=10
            )

            if not related:
                print("No relationships found for this file.")
                return False

            # Create a simple ASCII visualization
            print(f"  {self.file_path}")
            print("  |")
            
            # Group by relationship type
            rel_groups = {}
            for entity in related:
                if not hasattr(entity, "relationship"):
                    continue
                
                rel = entity.relationship
                if rel not in rel_groups:
                    rel_groups[rel] = []
                
                rel_groups[rel].append(entity)

            # Display grouped relationships
            for rel, entities in rel_groups.items():
                print(f"  ├── {rel}")
                
                for i, entity in enumerate(entities[:3]):
                    is_last = i == len(entities[:3]) - 1 and len(entities) <= 3
                    prefix = "  │   └── " if is_last else "  │   ├── "
                    
                    if hasattr(entity, "id") and entity.id.startswith("file:"):
                        name = entity.id.replace("file:", "")
                    elif hasattr(entity, "title"):
                        name = entity.title
                    else:
                        name = str(entity)
                    
                    print(f"{prefix}{name}")
                
                if len(entities) > 3:
                    print(f"  │   └── ... and {len(entities) - 3} more")

            return True

        except Exception as e:
            print(f"Error visualizing relationships: {e}")
            return False

    def suggest_next_steps(self) -> None:
        """Suggest next steps for the user."""
        print("\n=== Next Steps ===\n")
        print("Try these commands to explore further:")
        print(f"- arc why {self.file_path}:1")
        print(f"- arc relate file:{self.file_path}")
        print(f"- arc query \"Why was {os.path.basename(self.file_path)} created?\"")
        print("\nOr check out more examples in the docs/examples/ directory.")

    def run(self, file_path: Optional[str] = None, depth: int = 2, focus: str = "all") -> bool:
        """Run the Quick Win Demo.

        Args:
            file_path: Optional file path to analyze
            depth: Depth of analysis (1-3)
            focus: Focus of analysis (all, history, dependencies, decisions)

        Returns:
            True if the demo ran successfully, False otherwise
        """
        # Set parameters
        self.depth = max(1, min(3, depth))  # Clamp between 1 and 3
        self.focus = focus

        # Initialize Arc Memory
        if not self.initialize():
            return False

        # Find an interesting file
        if not self.find_interesting_file(file_path):
            return False

        # Analyze file history
        self.analyze_file_history()

        # Analyze dependencies
        self.analyze_dependencies()

        # Analyze decisions
        self.analyze_decisions()

        # Visualize relationships
        self.visualize_relationships()

        # Suggest next steps
        self.suggest_next_steps()

        print("\n=== Demo Complete ===\n")
        return True


def main():
    """Main entry point for the Quick Win Demo."""
    parser = argparse.ArgumentParser(description="Arc Memory Quick Win Demo")
    parser.add_argument("--file", type=str, help="Path to the file to analyze")
    parser.add_argument("--depth", type=int, default=2, choices=[1, 2, 3], help="Depth of analysis (1-3)")
    parser.add_argument("--focus", type=str, default="all", choices=["all", "history", "dependencies", "decisions"], help="Focus of analysis")
    args = parser.parse_args()

    # Create and run the Quick Win Demo
    demo = QuickWinDemo()
    success = demo.run(file_path=args.file, depth=args.depth, focus=args.focus)

    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
