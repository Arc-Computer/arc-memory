#!/usr/bin/env python3
"""
Code Time Machine Demo

This script demonstrates Arc Memory's temporal understanding capabilities by creating
a "time machine" experience that allows developers to explore how code evolved over time,
understand the reasoning behind key decisions, and visualize the potential impact of changes.

Usage:
    python code_time_machine.py [--repo PATH] [--file PATH] [--interactive]

Example:
    python code_time_machine.py --repo ./ --file arc_memory/sdk/core.py --interactive
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add colorama for terminal colors
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    print("Colorama not installed. Install with: pip install colorama")
    # Create mock colorama classes if not available
    class MockColorama:
        def __getattr__(self, name):
            return ""
    Fore = MockColorama()
    Back = MockColorama()
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
    from arc_memory.sdk.models import DecisionTrailEntry, HistoryEntry, ImpactResult
    from arc_memory.sdk.progress import ProgressCallback, ProgressStage
except ImportError:
    print(f"{Fore.RED}Error: Arc Memory SDK not found. Please install it with 'pip install arc-memory'.{Style.RESET_ALL}")
    sys.exit(1)

# Import visualizers

try:
    # Try relative import first (when imported as a module)
    from .visualizers.timeline_visualizer import visualize_timeline
    from .visualizers.decision_visualizer import visualize_decisions
    from .visualizers.impact_visualizer import visualize_impact
except ImportError:
    # Try direct import (when run as a script)
    from visualizers.timeline_visualizer import visualize_timeline
    from visualizers.decision_visualizer import visualize_decisions
    from visualizers.impact_visualizer import visualize_impact


# Import reasoning engine
try:
    # Try relative import first (when imported as a module)
    from .reasoning_engine import ReasoningEngine
    has_reasoning_engine = True
except ImportError:
    try:
        # Try direct import (when run as a script)
        from reasoning_engine import ReasoningEngine
        has_reasoning_engine = True
    except ImportError:
        print(f"{Fore.YELLOW}Warning: Reasoning Engine not found. Advanced analysis will be disabled.{Style.RESET_ALL}")
        has_reasoning_engine = False
        ReasoningEngine = None


class CodeTimeMachine:
    """Code Time Machine demo class."""

    def __init__(self, repo_path: str = "./", interactive: bool = False, use_reasoning: bool = True):
        """Initialize the Code Time Machine.

        Args:
            repo_path: Path to the repository
            interactive: Whether to run in interactive mode
            use_reasoning: Whether to use the reasoning engine for advanced analysis
        """
        self.repo_path = repo_path
        self.interactive = interactive
        self.use_reasoning = use_reasoning and has_reasoning_engine
        self.arc = None
        self.file_path = None
        self.reasoning_engine = None

    def initialize(self) -> bool:
        """Initialize Arc Memory and check if the knowledge graph exists.

        Returns:
            True if initialization was successful, False otherwise
        """
        console.print(Panel(f"[bold green]Initializing Code Time Machine[/bold green]"))

        try:
            # Initialize Arc Memory
            console.print(f"[blue]Connecting to Arc Memory knowledge graph...[/blue]")
            self.arc = Arc(repo_path=self.repo_path)

            # Initialize reasoning engine if enabled
            if self.use_reasoning:
                console.print(f"[blue]Initializing reasoning engine...[/blue]")
                self.reasoning_engine = ReasoningEngine(model="o4-mini")
                console.print(f"[green]Reasoning engine initialized successfully.[/green]")

            return True
        except Exception as e:
            console.print(f"[red]Error initializing: {e}[/red]")
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
            console.print(f"[green]Selected file: {self.file_path}[/green]")
            return self.file_path

        if not self.interactive:
            console.print("[red]No file specified and not in interactive mode.[/red]")
            return None

        # In interactive mode, let the user select a file
        console.print("[yellow]Please enter a file path to explore:[/yellow]")
        self.file_path = input("> ")

        # Check if the file exists
        if not os.path.exists(os.path.join(self.repo_path, self.file_path)):
            console.print(f"[red]File not found: {self.file_path}[/red]")
            return None

        console.print(f"[green]Selected file: {self.file_path}[/green]")
        return self.file_path

    def explore_timeline(self) -> bool:
        """Explore the timeline of the selected file.

        Returns:
            True if exploration was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        console.print(Panel(f"[bold green]Timeline Exploration: {self.file_path}[/bold green]"))

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[blue]Retrieving file history...", total=None)

                # Get file history using Arc Memory SDK
                entity_id = f"file:{self.file_path}"
                try:
                    history = self.arc.get_entity_history(entity_id=entity_id, include_related=True)
                    if not history:
                        console.print(f"[yellow]Warning: No history found for {entity_id}[/yellow]")
                        # Try to get related entities instead
                        console.print(f"[yellow]Trying to get related entities instead...[/yellow]")
                        related = self.arc.get_related_entities(
                            entity_id=entity_id,
                            max_distance=1,
                            max_results=10
                        )

                        if related:
                            # Convert related entities to history entries
                            from datetime import datetime
                            history = []
                            for entity in related:
                                # Create a history entry from the related entity
                                history.append(
                                    type('HistoryEntry', (), {
                                        'id': entity.id,
                                        'type': entity.type if hasattr(entity, 'type') else "unknown",
                                        'title': entity.title if hasattr(entity, 'title') else entity.id,
                                        'body': entity.body if hasattr(entity, 'body') else "",
                                        'timestamp': datetime.now().isoformat(),  # Current time as we don't know the actual time
                                        'properties': {},
                                        'change_type': "referenced",
                                        'related_entities': []
                                    })
                                )
                except Exception as e:
                    console.print(f"[red]Error retrieving file history: {e}[/red]")
                    history = []

                progress.update(task, completed=True)

            # Visualize the timeline
            visualize_timeline(history, self.file_path)

            # Use reasoning engine for advanced analysis if enabled
            if self.use_reasoning and self.reasoning_engine and history:
                console.print("\n[bold yellow]Advanced Timeline Analysis:[/bold yellow]")

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("[blue]Analyzing file history with reasoning model...", total=None)

                    # Analyze the history using the reasoning engine
                    analysis = self.reasoning_engine.analyze_file_history(self.file_path, history)

                    progress.update(task, completed=True)

                # Display the analysis
                console.print(Panel(
                    Markdown(analysis["text"]),
                    title="Reasoning Model Analysis",
                    border_style="green"
                ))

                # Display the reasoning summary if available
                if analysis["reasoning_summary"]:
                    console.print(Panel(
                        Markdown(analysis["reasoning_summary"]),
                        title="Reasoning Process",
                        border_style="blue"
                    ))

            return True

        except Exception as e:
            console.print(f"[red]Error exploring timeline: {e}[/red]")
            return False

    def explore_decisions(self) -> bool:
        """Explore key decisions that shaped the selected file.

        Returns:
            True if exploration was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        console.print(Panel(f"[bold green]Decision Archaeology: {self.file_path}[/bold green]"))

        try:
            # For demo purposes, we'll analyze a few key lines in the file
            # In a real implementation, we would identify significant lines automatically
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

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                for _, line_number in enumerate(line_numbers):
                    task = progress.add_task(
                        f"[blue]Analyzing line {line_number}...",
                        total=None
                    )

                    # Get decision trail using Arc Memory SDK
                    trail = self.arc.get_decision_trail(
                        file_path=self.file_path,
                        line_number=line_number,
                        max_results=3,
                        include_rationale=True
                    )

                    if trail:
                        decision_trails.append((line_number, trail))

                    progress.update(task, completed=True)

            # Visualize the decisions
            visualize_decisions(decision_trails, self.file_path)

            # Use reasoning engine for advanced analysis if enabled
            if self.use_reasoning and self.reasoning_engine and decision_trails:
                console.print("\n[bold yellow]Advanced Decision Analysis:[/bold yellow]")

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("[blue]Analyzing decisions with reasoning model...", total=None)

                    # Analyze the decisions using the reasoning engine
                    analysis = self.reasoning_engine.analyze_decisions(self.file_path, decision_trails)

                    progress.update(task, completed=True)

                # Display the analysis
                console.print(Panel(
                    Markdown(analysis["text"]),
                    title="Reasoning Model Analysis of Decisions",
                    border_style="green"
                ))

                # Display the reasoning summary if available
                if analysis["reasoning_summary"]:
                    console.print(Panel(
                        Markdown(analysis["reasoning_summary"]),
                        title="Reasoning Process",
                        border_style="blue"
                    ))

            return True

        except Exception as e:
            console.print(f"[red]Error exploring decisions: {e}[/red]")
            return False

    def predict_impact(self) -> bool:
        """Predict the impact of changes to the selected file.

        Returns:
            True if prediction was successful, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        console.print(Panel(f"[bold green]Impact Prediction: {self.file_path}[/bold green]"))

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[blue]Analyzing potential impact...", total=None)

                # Get impact analysis using our custom implementation
                component_id = f"file:{self.file_path}"
                try:
                    # Import our custom impact analysis
                    try:
                        # Try relative import first (when imported as a module)
                        from .custom_impact import analyze_component_impact
                    except ImportError:
                        # Try absolute import (when run as a module)
                        try:
                            from demo.code_time_machine.custom_impact import analyze_component_impact
                        except ImportError:
                            # Try direct import (when run as a script)
                            from custom_impact import analyze_component_impact

                    # Use our custom implementation
                    impact = analyze_component_impact(
                        adapter=self.arc.adapter,
                        component_id=component_id,
                        impact_types=["direct", "indirect", "potential"],
                        max_depth=3
                    )

                    if not impact:
                        console.print(f"[yellow]No impact results found using custom analysis. Trying Arc SDK...[/yellow]")
                        # Fall back to Arc SDK
                        impact = self.arc.analyze_component_impact(
                            component_id=component_id,
                            impact_types=["direct", "indirect"],
                            max_depth=3
                        )
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not analyze component impact: {e}[/yellow]")
                    # Try to get related entities instead
                    try:
                        console.print(f"[yellow]Trying to get related entities instead...[/yellow]")
                        related = self.arc.get_related_entities(
                            entity_id=component_id,
                            max_distance=2,
                            max_results=10
                        )

                        # Convert related entities to impact results
                        impact = []
                        for entity in related:
                            # Calculate impact score based on distance
                            distance = entity.distance if hasattr(entity, 'distance') else 1
                            impact_score = max(0.3, 0.9 - (distance * 0.3))

                            # Determine impact type
                            if distance <= 1:
                                impact_type = "direct"
                            else:
                                impact_type = "indirect"

                            # Create impact result
                            impact.append(
                                type('ImpactResult', (), {
                                    'id': entity.id,
                                    'title': entity.title if hasattr(entity, 'title') else entity.id,
                                    'impact_score': impact_score,
                                    'impact_type': impact_type,
                                    'impact_path': [component_id, entity.id]
                                })
                            )
                    except Exception as e2:
                        console.print(f"[red]Error getting related entities: {e2}[/red]")
                        impact = []

                progress.update(task, completed=True)

            # Visualize the impact
            visualize_impact(impact, self.file_path)

            # Use reasoning engine for advanced analysis if enabled
            if self.use_reasoning and self.reasoning_engine and impact:
                console.print("\n[bold yellow]Advanced Impact Analysis:[/bold yellow]")

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("[blue]Analyzing impact with reasoning model...", total=None)

                    # Analyze the impact using the reasoning engine
                    analysis = self.reasoning_engine.analyze_impact(self.file_path, impact)

                    progress.update(task, completed=True)

                # Display the analysis
                console.print(Panel(
                    Markdown(analysis["text"]),
                    title="Reasoning Model Impact Analysis",
                    border_style="green"
                ))

                # Display the reasoning summary if available
                if analysis["reasoning_summary"]:
                    console.print(Panel(
                        Markdown(analysis["reasoning_summary"]),
                        title="Reasoning Process",
                        border_style="blue"
                    ))

            return True

        except Exception as e:
            console.print(f"[red]Error predicting impact: {e}[/red]")
            return False

    def suggest_improvements(self) -> bool:
        """Suggest improvements based on historical patterns.

        Returns:
            True if suggestions were generated successfully, False otherwise
        """
        if not self.file_path or not self.arc:
            return False

        console.print(Panel(f"[bold green]Improvement Suggestions: {self.file_path}[/bold green]"))

        try:
            # Get file history and impact for reasoning engine
            entity_id = f"file:{self.file_path}"
            history = []
            impact = []
            file_content = ""

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                # Get file history
                task_history = progress.add_task("[blue]Retrieving file history...", total=None)
                try:
                    history = self.arc.get_entity_history(entity_id=entity_id, include_related=True)
                    if not history:
                        console.print(f"[yellow]Warning: No history found for {entity_id}[/yellow]")
                        # Try to get related entities instead
                        console.print(f"[yellow]Trying to get related entities instead...[/yellow]")
                        related = self.arc.get_related_entities(
                            entity_id=entity_id,
                            max_distance=1,
                            max_results=10
                        )

                        if related:
                            # Convert related entities to history entries
                            from datetime import datetime
                            history = []
                            for entity in related:
                                # Create a history entry from the related entity
                                history.append(
                                    type('HistoryEntry', (), {
                                        'id': entity.id,
                                        'type': entity.type if hasattr(entity, 'type') else "unknown",
                                        'title': entity.title if hasattr(entity, 'title') else entity.id,
                                        'body': entity.body if hasattr(entity, 'body') else "",
                                        'timestamp': datetime.now().isoformat(),  # Current time as we don't know the actual time
                                        'properties': {},
                                        'change_type': "referenced",
                                        'related_entities': []
                                    })
                                )
                except Exception as e:
                    console.print(f"[red]Error retrieving file history: {e}[/red]")
                    history = []
                progress.update(task_history, completed=True)

                # Get impact analysis
                task_impact = progress.add_task("[blue]Retrieving impact analysis...", total=None)
                component_id = f"file:{self.file_path}"
                try:
                    # Import our custom impact analysis
                    try:
                        # Try relative import first (when imported as a module)
                        from .custom_impact import analyze_component_impact
                    except ImportError:
                        # Try absolute import (when run as a module)
                        try:
                            from demo.code_time_machine.custom_impact import analyze_component_impact
                        except ImportError:
                            # Try direct import (when run as a script)
                            from custom_impact import analyze_component_impact

                    # Use our custom implementation
                    impact = analyze_component_impact(
                        adapter=self.arc.adapter,
                        component_id=component_id,
                        impact_types=["direct", "indirect", "potential"],
                        max_depth=3
                    )

                    if not impact:
                        console.print(f"[yellow]No impact results found using custom analysis. Trying Arc SDK...[/yellow]")
                        # Fall back to Arc SDK
                        impact = self.arc.analyze_component_impact(
                            component_id=component_id,
                            impact_types=["direct", "indirect"],
                            max_depth=3
                        )
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not analyze component impact: {e}[/yellow]")
                    # Try to get related entities instead
                    try:
                        console.print(f"[yellow]Trying to get related entities instead...[/yellow]")
                        related = self.arc.get_related_entities(
                            entity_id=component_id,
                            max_distance=2,
                            max_results=10
                        )

                        # Convert related entities to impact results
                        impact = []
                        for entity in related:
                            # Calculate impact score based on distance
                            distance = entity.distance if hasattr(entity, 'distance') else 1
                            impact_score = max(0.3, 0.9 - (distance * 0.3))

                            # Determine impact type
                            if distance <= 1:
                                impact_type = "direct"
                            else:
                                impact_type = "indirect"

                            # Create impact result
                            impact.append(
                                type('ImpactResult', (), {
                                    'id': entity.id,
                                    'title': entity.title if hasattr(entity, 'title') else entity.id,
                                    'impact_score': impact_score,
                                    'impact_type': impact_type,
                                    'impact_path': [component_id, entity.id]
                                })
                            )
                    except Exception as e2:
                        console.print(f"[red]Error getting related entities: {e2}[/red]")
                        impact = []
                progress.update(task_impact, completed=True)

                # Get file content
                task_content = progress.add_task("[blue]Reading file content...", total=None)
                file_path = os.path.join(self.repo_path, self.file_path)
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        file_content = f.read()
                progress.update(task_content, completed=True)

            # Use reasoning engine for advanced analysis if enabled
            if self.use_reasoning and self.reasoning_engine and (history or impact):
                console.print("\n[bold yellow]Advanced Improvement Suggestions:[/bold yellow]")

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("[blue]Generating suggestions with reasoning model...", total=None)

                    # Generate suggestions using the reasoning engine
                    suggestions = self.reasoning_engine.suggest_improvements(
                        self.file_path, file_content, history, impact
                    )

                    progress.update(task, completed=True)

                # Display the suggestions
                console.print(Panel(
                    Markdown(suggestions["text"]),
                    title="Reasoning Model Improvement Suggestions",
                    border_style="green"
                ))

                # Display the reasoning summary if available
                if suggestions["reasoning_summary"]:
                    console.print(Panel(
                        Markdown(suggestions["reasoning_summary"]),
                        title="Reasoning Process",
                        border_style="blue"
                    ))
            else:
                # Fallback to Arc Memory's query capability
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("[blue]Generating improvement suggestions...", total=None)

                    # Use Arc Memory's query capability to generate suggestions
                    query = f"Based on the history and patterns in {self.file_path}, what improvements could be made?"
                    result = self.arc.query(query)

                    progress.update(task, completed=True)

                # Display the suggestions
                console.print("\n[bold yellow]Suggested Improvements:[/bold yellow]")
                console.print(Markdown(result.answer))

            return True

        except Exception as e:
            console.print(f"[red]Error generating suggestions: {e}[/red]")
            return False

    def run_demo(self, file_path: Optional[str] = None) -> None:
        """Run the full Code Time Machine demo.

        Args:
            file_path: Optional file path to explore
        """
        # Step 1: Initialize
        if not self.initialize():
            console.print("[red]Failed to initialize. Exiting.[/red]")
            return

        # Step 2: Select a file
        if not self.select_file(file_path):
            console.print("[red]Failed to select a file. Exiting.[/red]")
            return

        # Step 3: Explore timeline
        self.explore_timeline()

        # Step 4: Explore decisions
        self.explore_decisions()

        # Step 5: Predict impact
        self.predict_impact()

        # Step 6: Suggest improvements
        self.suggest_improvements()

        # Demo complete
        console.print(Panel(f"[bold green]Code Time Machine Demo Complete[/bold green]"))


def main():
    """Main entry point for the Code Time Machine demo."""
    parser = argparse.ArgumentParser(description="Code Time Machine Demo")
    parser.add_argument("--repo", default="./", help="Path to the repository (default: current directory)")
    parser.add_argument("--file", help="Path to the file to explore")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--reasoning", action="store_true", default=True, help="Enable reasoning engine for advanced analysis")
    parser.add_argument("--no-reasoning", action="store_false", dest="reasoning", help="Disable reasoning engine")
    parser.add_argument("--model", default="o4-mini", help="Reasoning model to use (default: o4-mini)")

    args = parser.parse_args()

    # Check if OpenAI API key is set
    if args.reasoning and not os.environ.get("OPENAI_API_KEY"):
        console.print("[yellow]Warning: OPENAI_API_KEY environment variable is not set.[/yellow]")
        console.print("[yellow]Reasoning engine will be disabled.[/yellow]")
        console.print("[yellow]Set your OpenAI API key with: export OPENAI_API_KEY=your-api-key[/yellow]")
        args.reasoning = False

    # Create and run the Code Time Machine
    time_machine = CodeTimeMachine(repo_path=args.repo, interactive=args.interactive, use_reasoning=args.reasoning)
    time_machine.run_demo(file_path=args.file)


if __name__ == "__main__":
    main()
