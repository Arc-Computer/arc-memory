"""
Timeline Visualizer for Code Time Machine Demo

This module provides functions to visualize the timeline of a file's evolution.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

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


def parse_timestamp(timestamp: Optional[str]) -> Optional[datetime]:
    """Parse a timestamp string into a datetime object.
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        Datetime object or None if parsing fails
    """
    if not timestamp:
        return None
        
    try:
        # Handle ISO format with Z
        if isinstance(timestamp, str) and 'Z' in timestamp:
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp)
        elif isinstance(timestamp, datetime):
            return timestamp
    except ValueError:
        pass
        
    return None


def format_timestamp(timestamp: Optional[str]) -> str:
    """Format a timestamp for display.
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        Formatted timestamp string
    """
    dt = parse_timestamp(timestamp)
    if not dt:
        return "Unknown date"
        
    return dt.strftime("%Y-%m-%d")


def get_change_type_symbol(change_type: str) -> str:
    """Get a symbol representing the change type.
    
    Args:
        change_type: Type of change
        
    Returns:
        Symbol representing the change type
    """
    if change_type == "created":
        return "➕"
    elif change_type == "modified":
        return "✏️"
    elif change_type == "referenced":
        return "🔗"
    elif change_type == "deleted":
        return "❌"
    else:
        return "•"


def visualize_timeline(history: List[Any], file_path: str) -> None:
    """Visualize the timeline of a file's evolution.
    
    Args:
        history: List of history entries
        file_path: Path to the file
    """
    console.print("\n[bold yellow]File Evolution Timeline:[/bold yellow]")
    
    if not history:
        console.print("[yellow]No history found for this file.[/yellow]")
        return
    
    # Sort history by timestamp (newest first)
    sorted_history = sorted(
        history, 
        key=lambda x: parse_timestamp(x.timestamp) if hasattr(x, 'timestamp') else datetime.min,
        reverse=True
    )
    
    # Create a table for the timeline
    table = Table(title=f"Timeline for {file_path}")
    table.add_column("Date", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Change", style="yellow")
    table.add_column("Details", style="white")
    
    # Add entries to the table
    for entry in sorted_history:
        # Format the timestamp
        date = format_timestamp(entry.timestamp)
        
        # Get the change type symbol
        change_symbol = get_change_type_symbol(entry.change_type)
        
        # Format the details
        details = entry.title if hasattr(entry, 'title') and entry.title else ""
        if hasattr(entry, 'properties') and entry.properties:
            if 'author' in entry.properties:
                details += f" (by {entry.properties['author']})"
        
        # Add the row to the table
        table.add_row(
            date,
            entry.type if hasattr(entry, 'type') else "unknown",
            change_symbol,
            details
        )
    
    console.print(table)
    
    # Create an ASCII timeline visualization
    console.print("\n[bold yellow]Visual Timeline:[/bold yellow]")
    
    # Get unique timestamps
    timestamps = []
    for entry in sorted_history:
        ts = format_timestamp(entry.timestamp)
        if ts not in timestamps:
            timestamps.append(ts)
    
    # Create the timeline visualization
    timeline = ""
    for i, ts in enumerate(timestamps):
        # Find entries for this timestamp
        entries = [e for e in sorted_history if format_timestamp(e.timestamp) == ts]
        
        # Format the timestamp
        timeline += f"[{ts}] "
        
        # Add the entry titles
        entry_titles = []
        for entry in entries:
            title = entry.title if hasattr(entry, 'title') and entry.title else entry.type
            if len(title) > 30:
                title = title[:27] + "..."
            entry_titles.append(title)
        
        timeline += ", ".join(entry_titles)
        
        # Add the connector line
        if i < len(timestamps) - 1:
            timeline += " ─────"
            
            # Add branch lines for multiple entries
            if len(entries) > 1:
                timeline += "┬"
            else:
                timeline += "┐"
                
            timeline += "\n"
            timeline += " " * (len(ts) + 3) + "│\n"
        
    console.print(Markdown(f"```\n{timeline}\n```"))
    
    # Display a summary
    console.print(f"\n[bold green]Summary:[/bold green] Found {len(sorted_history)} events in the history of {file_path}")
