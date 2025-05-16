#!/usr/bin/env python3
"""
Code Relationships Demo

This script demonstrates Arc Memory's ability to understand dependencies and relationships
between different code components. It uses the get_related_entities method to identify
direct and indirect relationships between components in your codebase.

Usage:
    python code_relationships_demo.py [--file FILE_PATH] [--distance DISTANCE] [--repo REPO_PATH]

Example:
    python code_relationships_demo.py --file arc_memory/sdk/relationships.py --distance 2
"""

import argparse
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Environment variables must be set manually.")
    print("Install with: pip install python-dotenv")

# Add colorama for terminal colors
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    print("Colorama not installed. Install with: pip install colorama")
    # Create mock colorama classes if not available
    class MockColorama:
        def __getattr__(self, name):
            return ""
    Fore = MockColorama()
    Style = MockColorama()

# Add rich for terminal formatting
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    console = Console()
except ImportError:
    print("Rich not installed. Install with: pip install rich")
    sys.exit(1)

# Import Arc Memory SDK
try:
    from arc_memory.sdk import Arc
    from arc_memory.sdk.models import RelatedEntity
except ImportError:
    print(f"{Fore.RED}Error: Arc Memory SDK not found. Please install it with 'pip install arc-memory'.{Style.RESET_ALL}")
    sys.exit(1)

# Optional matplotlib for visualization
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import networkx as nx
    HAS_VISUALIZATION = True
except ImportError:
    print(f"{Fore.YELLOW}Warning: Matplotlib or NetworkX not installed. Visualization will be disabled.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Install with: pip install matplotlib networkx{Style.RESET_ALL}")
    HAS_VISUALIZATION = False


class CodeRelationshipsDemo:
    """Code Relationships Demo class."""

    def __init__(self, repo_path: str = "./"):
        """Initialize the Code Relationships Demo.

        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        self.arc = None
        self.file_path = None
        self.related_entities = None

    def initialize(self) -> bool:
        """Initialize Arc Memory and check if the knowledge graph exists.

        Returns:
            True if initialization was successful, False otherwise
        """
        console.print(Panel(f"[bold green]Initializing Code Relationships Demo[/bold green]"))

        try:
            # Initialize Arc Memory
            console.print(f"[blue]Connecting to Arc Memory knowledge graph...[/blue]")
            self.arc = Arc(repo_path=self.repo_path)
            return True
        except Exception as e:
            console.print(f"[red]Error initializing: {e}[/red]")
            return False

    def analyze_relationships(self, file_path: str, max_results: int = 50) -> bool:
        """Analyze the relationships of a file.

        Args:
            file_path: Path to the file to analyze
            max_results: Maximum number of related entities to retrieve

        Returns:
            True if analysis was successful, False otherwise
        """
        if not self.arc:
            console.print(f"[red]Arc Memory not initialized. Run initialize() first.[/red]")
            return False

        self.file_path = file_path
        console.print(Panel(f"[bold green]Analyzing Relationships: {self.file_path}[/bold green]"))

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[blue]Analyzing code relationships...", total=None)

                # Get component ID
                entity_id = f"file:{self.file_path}"

                # Get related entities
                self.related_entities = self.arc.get_related_entities(
                    entity_id=entity_id,
                    max_results=max_results
                )

                progress.update(task, completed=True)

            # Display results
            self.display_relationships()

            # Visualize results if matplotlib is available
            if HAS_VISUALIZATION and self.related_entities:
                self.visualize_relationship_network()

            return True
        except Exception as e:
            console.print(f"[red]Error analyzing relationships: {e}[/red]")
            return False

    def display_relationships(self) -> None:
        """Display the relationship analysis results."""
        if not self.related_entities:
            console.print(f"[yellow]No related entities found.[/yellow]")
            return

        # Create a table for the results
        table = Table(title=f"Code Relationships for {self.file_path}")
        table.add_column("Component", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Relationship", style="green")
        table.add_column("Direction", style="yellow")

        # Group results by relationship type
        imports = []
        imported_by = []
        depends_on = []
        depended_on_by = []
        other_relationships = []

        for entity in self.related_entities:
            rel_type = entity.relationship.lower() if hasattr(entity, 'relationship') else "unknown"
            direction = entity.direction if hasattr(entity, 'direction') else "unknown"

            if rel_type == "imports" and direction == "outgoing":
                imports.append(entity)
            elif rel_type == "imports" and direction == "incoming":
                imported_by.append(entity)
            elif rel_type in ["depends_on", "uses", "calls"] and direction == "outgoing":
                depends_on.append(entity)
            elif rel_type in ["depends_on", "uses", "calls"] and direction == "incoming":
                depended_on_by.append(entity)
            else:
                other_relationships.append(entity)

        # Add results to table
        if imports:
            table.add_row("[bold]Imports[/bold]", "", "", "")
            for entity in imports:
                table.add_row(
                    self._get_entity_title(entity),
                    self._get_entity_type(entity),
                    "Imports",
                    "→"
                )

        if imported_by:
            table.add_row("[bold]Imported By[/bold]", "", "", "")
            for entity in imported_by:
                table.add_row(
                    self._get_entity_title(entity),
                    self._get_entity_type(entity),
                    "Imported By",
                    "←"
                )

        if depends_on:
            table.add_row("[bold]Depends On[/bold]", "", "", "")
            for entity in depends_on:
                table.add_row(
                    self._get_entity_title(entity),
                    self._get_entity_type(entity),
                    entity.relationship,
                    "→"
                )

        if depended_on_by:
            table.add_row("[bold]Depended On By[/bold]", "", "", "")
            for entity in depended_on_by:
                table.add_row(
                    self._get_entity_title(entity),
                    self._get_entity_type(entity),
                    entity.relationship,
                    "←"
                )

        if other_relationships:
            table.add_row("[bold]Other Relationships[/bold]", "", "", "")
            for entity in other_relationships:
                table.add_row(
                    self._get_entity_title(entity),
                    self._get_entity_type(entity),
                    entity.relationship,
                    entity.direction
                )

        # Display the table
        console.print(table)

        # Display summary
        console.print(f"\n[bold green]Relationship Summary:[/bold green]")
        console.print(f"Total related components: {len(self.related_entities)}")
        console.print(f"Imports: {len(imports)}")
        console.print(f"Imported By: {len(imported_by)}")
        console.print(f"Depends On: {len(depends_on)}")
        console.print(f"Depended On By: {len(depended_on_by)}")
        console.print(f"Other Relationships: {len(other_relationships)}")

    def visualize_relationship_network(self) -> None:
        """Visualize the relationship network using matplotlib and networkx."""
        if not HAS_VISUALIZATION or not self.related_entities:
            return

        console.print(f"\n[bold green]Generating Relationship Network Visualization...[/bold green]")

        # Create a directed graph
        G = nx.DiGraph()

        # Add the target component as the central node
        target_id = f"file:{self.file_path}"
        G.add_node(target_id, label=os.path.basename(self.file_path), type="target")

        # Add nodes and edges for each related entity
        for entity in self.related_entities:
            entity_id = entity.id

            # Skip if the entity is the target
            if entity_id == target_id:
                continue

            # Add the entity node
            G.add_node(entity_id, label=self._get_entity_title(entity), type=self._get_entity_type(entity))

            # Add the edge based on direction
            if entity.direction == "outgoing":
                G.add_edge(target_id, entity_id, relationship=entity.relationship)
            else:
                G.add_edge(entity_id, target_id, relationship=entity.relationship)

        # Create the plot
        plt.figure(figsize=(12, 10))

        # Define node colors based on type
        node_colors = []
        for node in G.nodes():
            if G.nodes[node]['type'] == "target":
                node_colors.append('red')
            elif G.nodes[node]['type'] == "file":
                node_colors.append('blue')
            elif G.nodes[node]['type'] == "function":
                node_colors.append('green')
            elif G.nodes[node]['type'] == "class":
                node_colors.append('purple')
            else:
                node_colors.append('orange')

        # Define edge colors based on relationship
        edge_colors = []
        for u, v, data in G.edges(data=True):
            rel = data.get('relationship', '').lower()
            if rel == 'imports':
                edge_colors.append('blue')
            elif rel in ['depends_on', 'uses', 'calls']:
                edge_colors.append('green')
            elif rel in ['inherits_from', 'implements']:
                edge_colors.append('purple')
            else:
                edge_colors.append('orange')

        # Create the layout
        pos = nx.spring_layout(G, k=0.3, iterations=50)

        # Draw the graph
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=500, alpha=0.8)
        nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=2, alpha=0.5, arrows=True)
        nx.draw_networkx_labels(G, pos, labels=nx.get_node_attributes(G, 'label'), font_size=10)

        # Add a legend
        target_patch = mpatches.Patch(color='red', label='Target File')
        file_patch = mpatches.Patch(color='blue', label='File')
        function_patch = mpatches.Patch(color='green', label='Function')
        class_patch = mpatches.Patch(color='purple', label='Class')
        other_patch = mpatches.Patch(color='orange', label='Other')

        import_edge_patch = mpatches.Patch(color='blue', label='Imports')
        depends_edge_patch = mpatches.Patch(color='green', label='Depends On/Uses/Calls')
        inherits_edge_patch = mpatches.Patch(color='purple', label='Inherits/Implements')
        other_edge_patch = mpatches.Patch(color='orange', label='Other Relationship')

        plt.legend(handles=[target_patch, file_patch, function_patch, class_patch, other_patch,
                           import_edge_patch, depends_edge_patch, inherits_edge_patch, other_edge_patch],
                  loc='upper right')

        # Set title and save
        plt.title(f"Code Relationships: {os.path.basename(self.file_path)}")
        plt.axis('off')

        # Save the figure
        output_file = "code_relationships.png"
        plt.savefig(output_file, bbox_inches='tight')
        plt.close()

        console.print(f"[green]Visualization saved to {output_file}[/green]")

    def _get_entity_title(self, entity: RelatedEntity) -> str:
        """Get a readable title for an entity.

        Args:
            entity: The entity

        Returns:
            A readable title
        """
        if hasattr(entity, 'title') and entity.title:
            return entity.title

        # Extract the basename if it's a file
        if hasattr(entity, 'id') and entity.id.startswith("file:"):
            return os.path.basename(entity.id[5:])

        return str(entity.id) if hasattr(entity, 'id') else "Unknown"

    def _get_entity_type(self, entity: RelatedEntity) -> str:
        """Get the type of an entity.

        Args:
            entity: The entity

        Returns:
            The entity type
        """
        if hasattr(entity, 'type') and entity.type:
            return entity.type

        # Try to infer type from ID
        if hasattr(entity, 'id'):
            if entity.id.startswith("file:"):
                return "file"
            elif entity.id.startswith("function:"):
                return "function"
            elif entity.id.startswith("class:"):
                return "class"

        return "unknown"


def main():
    """Main entry point for the Code Relationships Demo."""
    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        console.print("[red]Warning: OPENAI_API_KEY environment variable not set.[/red]")
        console.print("[yellow]This demo will use Ollama as a fallback, but OpenAI is recommended for best results.[/yellow]")
        console.print("[yellow]Set your OpenAI API key with: export OPENAI_API_KEY=your-api-key[/yellow]")
        console.print("[yellow]Or create a .env file with: OPENAI_API_KEY=your-api-key[/yellow]")
        console.print("")
    else:
        console.print("[green]OpenAI API key detected. Using OpenAI o4-mini model for optimal results.[/green]")
        console.print("")

        # Set the OPENAI_MODEL environment variable to use o4-mini
        os.environ["OPENAI_MODEL"] = "o4-mini"
        console.print("[yellow]Using o4-mini model - this model does not support temperature parameter.[/yellow]")

    parser = argparse.ArgumentParser(description="Code Relationships Demo")
    parser.add_argument("--file", default="arc_memory/sdk/relationships.py",
                        help="Path to the file to analyze (default: arc_memory/sdk/relationships.py)")
    parser.add_argument("--results", type=int, default=50,
                        help="Maximum number of related entities to retrieve (default: 50)")
    parser.add_argument("--repo", default="./",
                        help="Path to the repository (default: current directory)")

    args = parser.parse_args()

    # Create and run the Code Relationships Demo
    demo = CodeRelationshipsDemo(repo_path=args.repo)
    if demo.initialize():
        demo.analyze_relationships(file_path=args.file, max_results=args.results)

    console.print(Panel(f"[bold green]Code Relationships Demo Complete[/bold green]"))


if __name__ == "__main__":
    main()
