"""
Timeline visualization for the Simple Code Time Machine demo.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from utils import format_date, get_entity_property, truncate_text, extract_author, extract_title
except ImportError:
    from .utils import format_date, get_entity_property, truncate_text, extract_author, extract_title


def visualize_timeline(history: List[Any], file_path: str) -> None:
    """Visualize the timeline of a file.

    Args:
        history: List of history entries for the file
        file_path: Path to the file
    """
    print(f"=== File Timeline: {file_path} ===\n")

    if not history:
        print("No history found for this file.")
        print("This could be because:")
        print("1. The file is new and has no history yet")
        print("2. The knowledge graph doesn't have information about this file")
        print("3. The file path might be incorrect")
        print("\nTry running 'arc build' to update the knowledge graph.")
        return

    # Sort history by timestamp if available
    sorted_history = sorted(
        history,
        key=lambda x: get_entity_property(x, "timestamp", ""),
        reverse=False
    )

    # Group events by date
    events_by_date = {}
    for entry in sorted_history:
        # Get timestamp
        timestamp = get_entity_property(entry, "timestamp")
        if not timestamp:
            continue

        # Format date
        date = format_date(timestamp)

        # Get event type
        event_type = get_entity_property(entry, "type", "unknown")

        # Get author
        author = extract_author(entry)

        # Get title/message
        title = extract_title(entry)

        # Get related entities
        related = get_entity_property(entry, "related_entities", [])

        # Add to events by date
        if date not in events_by_date:
            events_by_date[date] = []

        events_by_date[date].append({
            "type": event_type,
            "author": author,
            "title": title,
            "related": related
        })

    # Display timeline
    for date, events in sorted(events_by_date.items()):
        for event in events:
            # Display event
            print(f"{date}: {event['type'].capitalize()} by {event['author']}")
            print(f"  - {event['title']}")

            # Display related entities
            for related in event['related'][:3]:  # Limit to 3 related entities
                related_type = get_entity_property(related, "type", "")
                related_title = extract_title(related)

                if related_type.lower() in ["pr", "pull_request", "issue"]:
                    related_number = get_entity_property(related, "number", "")
                    print(f"  - Related {related_type}: \"{related_title}\" (#{related_number})")

            print()

    print("Timeline visualization complete.")
    print("Note: This is a simplified view of the file's history.")
    print("For more detailed information, use 'arc trace' command.")
