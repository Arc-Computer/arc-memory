"""
Decision Visualizer for Code Time Machine Demo

This module provides functions to visualize the decision trails for a file.
"""

from typing import Dict, List, Optional, Any, Tuple

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    console = Console()
except ImportError:
    print("Rich not installed. Install with: pip install rich")
    import sys
    sys.exit(1)

try:
    from colorama import Fore, Style
except ImportError:
    # Create mock colorama classes if not available
    class MockColorama:
        def __getattr__(self, name):
            return ""
    Fore = MockColorama()
    Style = MockColorama()


def format_decision_trail(trail: List[Any], line_number: int) -> str:
    """Format a decision trail for display.

    Args:
        trail: List of decision trail entries
        line_number: Line number being analyzed

    Returns:
        Formatted decision trail as markdown
    """
    if not trail:
        return f"No decision trail found for line {line_number}."

    markdown = f"## Decision Trail for Line {line_number}\n\n"

    for i, entry in enumerate(trail):
        # Add entry header
        markdown += f"### {i+1}. {entry.title}\n\n"

        # Add entry type and ID
        markdown += f"**Type:** {entry.type}\n\n"

        # Add rationale if available
        if hasattr(entry, 'rationale') and entry.rationale:
            markdown += f"**Rationale:** {entry.rationale}\n\n"

        # Add properties based on type
        if entry.type == "commit":
            if hasattr(entry, 'properties'):
                if 'author' in entry.properties:
                    markdown += f"**Author:** {entry.properties['author']}\n\n"
                if 'sha' in entry.properties:
                    markdown += f"**Commit:** {entry.properties['sha'][:7]}\n\n"

        elif entry.type == "pr":
            if hasattr(entry, 'properties'):
                if 'number' in entry.properties:
                    markdown += f"**PR:** #{entry.properties['number']}\n\n"
                if 'state' in entry.properties:
                    markdown += f"**State:** {entry.properties['state']}\n\n"
                if 'url' in entry.properties:
                    markdown += f"**URL:** {entry.properties['url']}\n\n"

        elif entry.type == "issue":
            if hasattr(entry, 'properties'):
                if 'number' in entry.properties:
                    markdown += f"**Issue:** #{entry.properties['number']}\n\n"
                if 'state' in entry.properties:
                    markdown += f"**State:** {entry.properties['state']}\n\n"
                if 'url' in entry.properties:
                    markdown += f"**URL:** {entry.properties['url']}\n\n"

        elif entry.type == "adr":
            if hasattr(entry, 'properties'):
                if 'status' in entry.properties:
                    markdown += f"**Status:** {entry.properties['status']}\n\n"
                if 'decision_makers' in entry.properties:
                    decision_makers = entry.properties['decision_makers']
                    if isinstance(decision_makers, list):
                        markdown += f"**Decision Makers:** {', '.join(decision_makers)}\n\n"

        # Add separator between entries
        if i < len(trail) - 1:
            markdown += "---\n\n"

    return markdown


def visualize_decisions(decision_trails: List[Tuple[int, List[Any]]], file_path: str) -> None:
    """Visualize the decision trails for a file.

    Args:
        decision_trails: List of tuples containing line numbers and their decision trails
        file_path: Path to the file
    """
    console.print("\n[bold yellow]Key Decisions That Shaped This File:[/bold yellow]")

    if not decision_trails:
        console.print("[yellow]No decision trails found for this file.[/yellow]")
        return

    # Create a summary table
    table = Table(title=f"Decision Points in {file_path}")
    table.add_column("Line", style="cyan")
    table.add_column("Decision", style="green")
    table.add_column("Author", style="yellow")
    table.add_column("Date", style="white")

    # Add entries to the table
    for line_number, trail in decision_trails:
        if not trail:
            continue

        # Get the first entry (most recent decision)
        entry = trail[0]

        # Get the decision title
        decision = entry.title if hasattr(entry, 'title') and entry.title else "Unknown"

        # Get the author
        author = "Unknown"
        if hasattr(entry, 'properties') and entry.properties:
            if 'author' in entry.properties:
                author = entry.properties['author']

        # Get the date
        date = "Unknown"
        if hasattr(entry, 'timestamp') and entry.timestamp:
            from datetime import datetime
            try:
                # Handle ISO format with Z
                if isinstance(entry.timestamp, str) and 'Z' in entry.timestamp:
                    dt = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                elif isinstance(entry.timestamp, str):
                    dt = datetime.fromisoformat(entry.timestamp)
                else:
                    # Handle non-string timestamp
                    dt = entry.timestamp if isinstance(entry.timestamp, datetime) else None
                if dt:
                    date = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        # Add the row to the table
        table.add_row(
            str(line_number),
            decision,
            author,
            date
        )

    console.print(table)

    # Display detailed decision trails
    for line_number, trail in decision_trails:
        if not trail:
            continue

        # Format the decision trail
        markdown = format_decision_trail(trail, line_number)

        # Display the decision trail
        console.print(Panel(
            Markdown(markdown),
            title=f"Decision Trail for Line {line_number}",
            border_style="green"
        ))

        # Add a separator between decision trails
        console.print()

    # Display a summary
    console.print(f"\n[bold green]Summary:[/bold green] Found {len(decision_trails)} key decision points in {file_path}")
