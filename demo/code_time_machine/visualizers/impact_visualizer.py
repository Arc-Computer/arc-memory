"""
Impact Visualizer for Code Time Machine Demo

This module provides functions to visualize the potential impact of changes to a file.
"""

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


def get_impact_color(impact_score: float) -> str:
    """Get a color based on the impact score.

    Args:
        impact_score: Impact score (0.0 to 1.0)

    Returns:
        Color string for the impact score
    """
    if impact_score >= 0.8:
        return "red"
    elif impact_score >= 0.5:
        return "yellow"
    else:
        return "green"


def visualize_impact(impact_results: List[Any], file_path: str) -> None:
    """Visualize the potential impact of changes to a file.

    Args:
        impact_results: List of impact results
        file_path: Path to the file
    """
    console.print("\n[bold yellow]Potential Impact of Changes:[/bold yellow]")

    if not impact_results:
        console.print("[yellow]No impact analysis available for this file.[/yellow]")
        return

    # Create a table for the impact results
    table = Table(title=f"Impact Analysis for {file_path}")
    table.add_column("Component", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Impact Score", style="yellow")
    table.add_column("Path", style="white")

    # Add entries to the table
    for result in impact_results:
        # Get the impact color
        impact_color = get_impact_color(result.impact_score)

        # Format the impact path
        impact_path = " → ".join(result.impact_path) if hasattr(result, 'impact_path') and result.impact_path else ""

        # Add the row to the table
        table.add_row(
            result.title if hasattr(result, 'title') and result.title else "Unknown",
            result.impact_type if hasattr(result, 'impact_type') and result.impact_type else "Unknown",
            f"[{impact_color}]{result.impact_score:.2f}[/{impact_color}]",
            impact_path
        )

    console.print(table)

    # Create an ASCII impact visualization
    console.print("\n[bold yellow]Impact Visualization:[/bold yellow]")

    # Sort results by impact score (highest first)
    sorted_results = sorted(
        impact_results,
        key=lambda x: x.impact_score if hasattr(x, 'impact_score') else 0.0,
        reverse=True
    )

    # Get the top 5 results
    top_results = sorted_results[:5]

    # Create the impact visualization
    visualization = f"```\n{file_path}\n"

    for i, result in enumerate(top_results):
        # Get the impact color
        impact_color = get_impact_color(result.impact_score)

        # Format the component name
        component = result.title if hasattr(result, 'title') and result.title else "Unknown"
        if len(component) > 30:
            component = component[:27] + "..."

        # Add the connector line
        indent = " " * (i + 1)
        if i == 0:
            visualization += f"├─→ {component} ({result.impact_score:.2f})\n"
        else:
            visualization += f"{indent}├─→ {component} ({result.impact_score:.2f})\n"

    visualization += "```"

    console.print(Markdown(visualization))

    # Group results by impact type
    impact_by_type = {}
    for result in impact_results:
        impact_type = result.impact_type if hasattr(result, 'impact_type') and result.impact_type else "unknown"
        if impact_type not in impact_by_type:
            impact_by_type[impact_type] = []
        impact_by_type[impact_type].append(result)

    # Display summary by impact type
    console.print("\n[bold yellow]Impact Summary by Type:[/bold yellow]")

    for impact_type, results in impact_by_type.items():
        # Calculate average impact score
        avg_score = sum(r.impact_score for r in results) / len(results)

        # Get the impact color
        impact_color = get_impact_color(avg_score)

        # Display the summary
        console.print(f"[bold]{impact_type.capitalize()}[/bold]: {len(results)} components affected, average impact score: [{impact_color}]{avg_score:.2f}[/{impact_color}]")

    # Display a summary
    console.print(f"\n[bold green]Summary:[/bold green] Found {len(impact_results)} components that would be affected by changes to {file_path}")

    # Display risk assessment
    high_risk = [r for r in impact_results if hasattr(r, 'impact_score') and r.impact_score >= 0.8]
    medium_risk = [r for r in impact_results if hasattr(r, 'impact_score') and 0.5 <= r.impact_score < 0.8]
    low_risk = [r for r in impact_results if hasattr(r, 'impact_score') and r.impact_score < 0.5]

    console.print("\n[bold yellow]Risk Assessment:[/bold yellow]")
    console.print(f"[red]High Risk[/red]: {len(high_risk)} components")
    console.print(f"[yellow]Medium Risk[/yellow]: {len(medium_risk)} components")
    console.print(f"[green]Low Risk[/green]: {len(low_risk)} components")
