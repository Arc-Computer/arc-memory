"""
Decision visualization for the Simple Code Time Machine demo.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from utils import format_date, get_entity_property, truncate_text, extract_author, extract_title
except ImportError:
    from .utils import format_date, get_entity_property, truncate_text, extract_author, extract_title


def visualize_decisions(decision_trails: List[Tuple[int, List[Any]]], file_path: str) -> None:
    """Visualize the decision trails for a file.

    Args:
        decision_trails: List of (line_number, decision_trail) tuples
        file_path: Path to the file
    """
    print(f"=== Key Decisions for {file_path} ===\n")

    if not decision_trails:
        print("No decision trails found for this file.")
        print("This could be because:")
        print("1. The file has no significant decision history")
        print("2. The knowledge graph doesn't have decision information")
        print("3. The selected lines don't correspond to important decisions")
        print("\nTry running 'arc why' on specific lines of interest.")
        return

    # Process each decision trail
    for line_number, trail in decision_trails:
        if not trail:
            continue

        # Process each decision in the trail
        for decision in trail:
            # Get decision properties
            title = get_entity_property(decision, "title", "Unknown decision")
            rationale = get_entity_property(decision, "rationale", "No rationale provided")
            importance = get_entity_property(decision, "importance", 0.5)
            author = extract_author(decision)

            # Get timestamp
            timestamp = get_entity_property(decision, "timestamp")
            date = format_date(timestamp) if timestamp else "Unknown date"

            # Get related entities
            related = get_entity_property(decision, "related_entities", [])

            # Display decision
            print(f"Decision: {title} (Line {line_number})")
            print(f"Author: {author}")
            print(f"Date: {date}")
            print(f"Rationale: \"{rationale}\"")

            # Display related entities
            for related_entity in related[:2]:  # Limit to 2 related entities
                related_type = get_entity_property(related_entity, "type", "")
                related_title = extract_title(related_entity)

                if related_type and related_title:
                    print(f"Related {related_type}: {related_title}")

            print()

    print("Decision visualization complete.")
    print("Note: This is a simplified view of the decisions that shaped this file.")
    print("For more detailed information, use 'arc why file <file_path> <line_number>' command.")
