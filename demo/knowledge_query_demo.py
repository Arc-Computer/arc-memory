#!/usr/bin/env python3
"""
Knowledge Graph Query Demo

This script demonstrates Arc Memory's ability to answer natural language questions about
your codebase using the query method. It shows how to extract insights from the knowledge
graph using simple English questions.

Usage:
    python knowledge_query_demo.py [--query QUERY] [--interactive] [--repo REPO_PATH]

Example:
    python knowledge_query_demo.py --query "What changed in the last month?"
    python knowledge_query_demo.py --interactive
"""

import argparse
import os
import sys
import time
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
    from arc_memory.sdk.models import QueryResult
except ImportError:
    print(f"{Fore.RED}Error: Arc Memory SDK not found. Please install it with 'pip install arc-memory'.{Style.RESET_ALL}")
    sys.exit(1)


# Sample queries to demonstrate the capabilities
SAMPLE_QUERIES = [
    "What changed in the last month?",
    "How does the component impact analysis work?",
    "What are the key dependencies of the SDK module?",
    "What is the purpose of the get_related_entities function?",
    "What were the major architectural decisions in this project?",
    "How is authentication handled in the codebase?",
    "What are the most frequently modified files?",
    "How does the database adapter pattern work?",
    "What is the relationship between the SDK and the CLI?",
    "What are the main data models used in the codebase?"
]


class KnowledgeQueryDemo:
    """Knowledge Graph Query Demo class."""

    def __init__(self, repo_path: str = "./", interactive: bool = False):
        """Initialize the Knowledge Graph Query Demo.

        Args:
            repo_path: Path to the repository
            interactive: Whether to run in interactive mode
        """
        self.repo_path = repo_path
        self.interactive = interactive
        self.arc = None
        self.query_history = []

    def initialize(self) -> bool:
        """Initialize Arc Memory and check if the knowledge graph exists.

        Returns:
            True if initialization was successful, False otherwise
        """
        console.print(Panel(f"[bold green]Initializing Knowledge Graph Query Demo[/bold green]"))

        try:
            # Initialize Arc Memory
            console.print(f"[blue]Connecting to Arc Memory knowledge graph...[/blue]")
            self.arc = Arc(repo_path=self.repo_path)
            return True
        except Exception as e:
            console.print(f"[red]Error initializing: {e}[/red]")
            return False

    def run_query(self, query: str) -> Optional[QueryResult]:
        """Run a natural language query against the knowledge graph.

        Args:
            query: The natural language query

        Returns:
            The query result or None if the query failed
        """
        if not self.arc:
            console.print(f"[red]Arc Memory not initialized. Run initialize() first.[/red]")
            return None

        console.print(Panel(f"[bold green]Query: {query}[/bold green]"))

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[blue]Processing query...", total=None)

                # Run the query
                result = self.arc.query(query)

                progress.update(task, completed=True)

            # Add to query history
            self.query_history.append((query, result))

            # Display the result
            self.display_query_result(result)

            return result
        except Exception as e:
            console.print(f"[red]Error running query: {e}[/red]")
            return None

    def display_query_result(self, result: QueryResult) -> None:
        """Display the query result.

        Args:
            result: The query result
        """
        if not result:
            console.print(f"[yellow]No result available.[/yellow]")
            return

        # Display the answer
        console.print(Panel(
            Markdown(result.answer),
            title="Answer",
            border_style="green"
        ))

        # Display confidence if available
        if hasattr(result, 'confidence') and result.confidence is not None:
            confidence_level = self._get_confidence_level(result.confidence)
            console.print(f"[bold]Confidence:[/bold] {confidence_level} ({result.confidence:.2f})")

        # Display evidence if available
        if hasattr(result, 'evidence') and result.evidence:
            console.print("\n[bold yellow]Supporting Evidence:[/bold yellow]")

            # Create a table for the evidence
            table = Table()
            table.add_column("Source", style="cyan")
            table.add_column("Content", style="green")
            table.add_column("Relevance", style="yellow")

            # Check if we have any valid evidence
            has_valid_evidence = False

            for evidence in result.evidence:
                # Try to extract source - check multiple possible keys
                source = (
                    evidence.get('source') or
                    evidence.get('title') or
                    evidence.get('id') or
                    evidence.get('type', 'Unknown')
                )

                # Try to extract content - check multiple possible keys
                content = (
                    evidence.get('content') or
                    evidence.get('snippet') or
                    evidence.get('body') or
                    evidence.get('text', '')
                )

                # Truncate if too long
                if len(content) > 100:
                    content = content[:97] + "..."

                # Try to extract relevance score - check multiple possible keys
                relevance = (
                    evidence.get('relevance') or
                    evidence.get('score') or
                    evidence.get('confidence', 0.0)
                )

                # Only add row if we have some content
                if content or source != 'Unknown':
                    table.add_row(str(source), str(content), f"{float(relevance):.2f}")
                    has_valid_evidence = True

            # Only print the table if we have valid evidence
            if has_valid_evidence:
                console.print(table)
            else:
                # Create mock evidence for demonstration purposes
                console.print("[yellow]No detailed evidence available from the knowledge graph.[/yellow]")

                # Create a table with mock evidence based on the answer
                mock_table = Table()
                mock_table.add_column("Source", style="cyan")
                mock_table.add_column("Content", style="green")
                mock_table.add_column("Note", style="yellow")

                mock_table.add_row(
                    "SDK Documentation",
                    "The analyze_component_impact function predicts the potential impact of changes...",
                    "Mock data for demo"
                )
                mock_table.add_row(
                    "Code Comments",
                    "This method identifies components that may be affected by changes to the specified component...",
                    "Mock data for demo"
                )
                mock_table.add_row(
                    "PR #42",
                    "Added blast radius prediction capability through analyze_component_impact...",
                    "Mock data for demo"
                )

                console.print(mock_table)

        # Display query understanding if available
        if hasattr(result, 'query_understanding') and result.query_understanding:
            console.print(Panel(
                Markdown(result.query_understanding),
                title="Query Understanding",
                border_style="blue"
            ))

        # Display reasoning if available
        if hasattr(result, 'reasoning') and result.reasoning:
            console.print(Panel(
                Markdown(result.reasoning),
                title="Reasoning Process",
                border_style="magenta"
            ))

    def run_interactive_mode(self) -> None:
        """Run the demo in interactive mode."""
        console.print(Panel(f"[bold green]Interactive Query Mode[/bold green]"))
        console.print("[blue]Type your questions about the codebase. Type 'exit' to quit.[/blue]")

        # Display sample queries
        console.print("\n[bold yellow]Sample Queries:[/bold yellow]")
        for i, query in enumerate(SAMPLE_QUERIES, 1):
            console.print(f"{i}. {query}")

        while True:
            console.print("\n[bold green]Enter your query:[/bold green]")
            user_input = input("> ")

            if user_input.lower() in ['exit', 'quit', 'q']:
                break

            # Check if the user entered a number to select a sample query
            try:
                query_index = int(user_input) - 1
                if 0 <= query_index < len(SAMPLE_QUERIES):
                    user_input = SAMPLE_QUERIES[query_index]
                    console.print(f"[blue]Selected query: {user_input}[/blue]")
            except ValueError:
                pass

            # Run the query
            self.run_query(user_input)

    def run_demo(self, query: Optional[str] = None) -> None:
        """Run the Knowledge Graph Query Demo.

        Args:
            query: Optional query to run
        """
        # Step 1: Initialize
        if not self.initialize():
            console.print("[red]Failed to initialize. Exiting.[/red]")
            return

        # Step 2: Run query or interactive mode
        if self.interactive:
            self.run_interactive_mode()
        elif query:
            self.run_query(query)
        else:
            # Run a few sample queries
            console.print("[blue]Running sample queries to demonstrate capabilities...[/blue]")
            for query in SAMPLE_QUERIES[:3]:  # Run the first 3 sample queries
                self.run_query(query)
                time.sleep(1)  # Add a small delay between queries

        # Demo complete
        console.print(Panel(f"[bold green]Knowledge Graph Query Demo Complete[/bold green]"))

    def _get_confidence_level(self, confidence: float) -> str:
        """Get a confidence level label based on the confidence score.

        Args:
            confidence: The confidence score

        Returns:
            A confidence level label
        """
        if confidence >= 0.8:
            return "🟢 High"
        elif confidence >= 0.5:
            return "🟡 Medium"
        else:
            return "🔴 Low"


def main():
    """Main entry point for the Knowledge Graph Query Demo."""
    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        console.print("[red]Warning: OPENAI_API_KEY environment variable not set.[/red]")
        console.print("[yellow]This demo requires OpenAI for natural language queries.[/yellow]")
        console.print("[yellow]Set your OpenAI API key with: export OPENAI_API_KEY=your-api-key[/yellow]")
        console.print("[yellow]Or create a .env file with: OPENAI_API_KEY=your-api-key[/yellow]")
        console.print("")
        # This demo specifically needs OpenAI to work well
        if input("Continue anyway? (y/n): ").lower() != 'y':
            console.print("[red]Exiting demo.[/red]")
            sys.exit(1)
    else:
        console.print("[green]OpenAI API key detected. Using OpenAI o4-mini model for optimal results.[/green]")
        console.print("")

        # Set the OPENAI_MODEL environment variable to use o4-mini
        os.environ["OPENAI_MODEL"] = "o4-mini"
        console.print("[yellow]Using o4-mini model.[/yellow]")

    parser = argparse.ArgumentParser(description="Knowledge Graph Query Demo")
    parser.add_argument("--query",
                        help="Natural language query to run")
    parser.add_argument("--interactive", action="store_true",
                        help="Run in interactive mode")
    parser.add_argument("--repo", default="./",
                        help="Path to the repository (default: current directory)")

    args = parser.parse_args()

    # Create and run the Knowledge Graph Query Demo
    demo = KnowledgeQueryDemo(repo_path=args.repo, interactive=args.interactive)
    demo.run_demo(query=args.query)


if __name__ == "__main__":
    main()
