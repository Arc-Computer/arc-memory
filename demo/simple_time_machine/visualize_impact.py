"""
Impact visualization for the Simple Code Time Machine demo.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from .utils import get_entity_property, truncate_text


def visualize_impact(impact_results: List[Any], file_path: str) -> None:
    """Visualize the impact of changes to a file.

    Args:
        impact_results: List of impact results
        file_path: Path to the file
    """
    print(f"=== Impact Analysis for {file_path} ===\n")

    if not impact_results:
        print("No impact results found for this file.")
        print("This could be because:")
        print("1. The file has no dependencies or dependents")
        print("2. The knowledge graph doesn't have relationship information")
        print("3. The impact analysis couldn't find relevant connections")
        print("\nTry running 'arc relate file:<file_path>' for more information.")
        return

    # Group impact results by severity
    high_impact = []
    medium_impact = []
    low_impact = []

    for result in impact_results:
        # Get impact properties
        impact_score = get_entity_property(result, "impact_score", 0.0)
        if isinstance(impact_score, str):
            try:
                impact_score = float(impact_score)
            except ValueError:
                impact_score = 0.5  # Default to medium if can't parse
        
        # Get entity ID and title
        entity_id = get_entity_property(result, "id", "")
        title = get_entity_property(result, "title", entity_id)
        
        # Get impact type
        impact_type = get_entity_property(result, "impact_type", "unknown")
        
        # Get relationship type if available
        relationship = get_entity_property(result, "relationship", "")
        
        # Create impact entry
        impact_entry = {
            "id": entity_id,
            "title": title,
            "score": impact_score,
            "type": impact_type,
            "relationship": relationship
        }
        
        # Group by severity
        if impact_score >= 0.7:
            high_impact.append(impact_entry)
        elif impact_score >= 0.4:
            medium_impact.append(impact_entry)
        else:
            low_impact.append(impact_entry)

    # Sort each group by impact score
    high_impact.sort(key=lambda x: x["score"], reverse=True)
    medium_impact.sort(key=lambda x: x["score"], reverse=True)
    low_impact.sort(key=lambda x: x["score"], reverse=True)

    # Display high impact components
    if high_impact:
        print("High Impact Components:")
        for entry in high_impact:
            component_id = entry["id"].replace("file:", "")
            print(f"- {component_id} ({entry['score']:.1f})", end="")
            
            if entry["relationship"]:
                print(f" - {entry['relationship']}")
            elif entry["type"]:
                print(f" - {entry['type']} dependency")
            else:
                print()
        print()

    # Display medium impact components
    if medium_impact:
        print("Medium Impact Components:")
        for entry in medium_impact:
            component_id = entry["id"].replace("file:", "")
            print(f"- {component_id} ({entry['score']:.1f})", end="")
            
            if entry["relationship"]:
                print(f" - {entry['relationship']}")
            elif entry["type"]:
                print(f" - {entry['type']} dependency")
            else:
                print()
        print()

    # Display low impact components
    if low_impact:
        print("Low Impact Components:")
        for entry in low_impact:
            component_id = entry["id"].replace("file:", "")
            print(f"- {component_id} ({entry['score']:.1f})", end="")
            
            if entry["relationship"]:
                print(f" - {entry['relationship']}")
            elif entry["type"]:
                print(f" - {entry['type']} dependency")
            else:
                print()
        print()

    print("Impact visualization complete.")
    print("Note: This is a simplified view of the potential impact of changes to this file.")
    print("For more detailed analysis, use 'arc analyze-impact file:<file_path>' command.")
