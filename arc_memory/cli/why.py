"""Why command for Arc Memory CLI.

This command provides a user-friendly way to trace the history of a specific line in a file,
showing the decision trail through commits, PRs, issues, and ADRs.
"""

import json
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.telemetry import track_command_usage
from arc_memory.trace import trace_history_for_file_line

class Format(str, Enum):
    """Output format for why results."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


app = typer.Typer(help="Show decision trail for a file line")
console = Console()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Show decision trail for a file line."""
    configure_logging(debug=is_debug_mode())


@app.command()
def file(
    file_path: str = typer.Argument(..., help="Path to the file"),
    line_number: int = typer.Argument(..., help="Line number to trace"),
    max_results: int = typer.Option(
        5, "--max-results", "-m", help="Maximum number of results to return"
    ),
    max_hops: int = typer.Option(
        3, "--max-hops", "-h", help="Maximum number of hops in the graph traversal"
    ),
    format: Format = typer.Option(
        Format.TEXT, "--format", "-f",
        help="Output format (text, json, or markdown)"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging"
    ),
) -> None:
    """Show the decision trail for a specific line in a file.

    This command traces the history of a specific line in a file, showing the commit
    that last modified it and related entities such as PRs, issues, and ADRs.

    Examples:
        arc why file src/main.py 42
        arc why file src/main.py 42 --format markdown
        arc why file src/main.py 42 --max-results 10 --max-hops 4
    """
    configure_logging(debug=debug)

    # Track command usage
    context = {
        "file_path": file_path,
        "line_number": line_number,
        "max_results": max_results,
        "max_hops": max_hops,
        "format": format.value
    }
    track_command_usage("why_file", context=context)

    try:
        # Get the database path
        from arc_memory.sql.db import ensure_arc_dir
        arc_dir = ensure_arc_dir()
        db_path = arc_dir / "graph.db"

        # Check if the database exists
        if not db_path.exists():
            error_msg = f"Error: Database not found at {db_path}"
            if format == Format.JSON:
                # For JSON format, print errors to stderr
                print(error_msg, file=sys.stderr)
            else:
                # For text format, use rich console
                console.print(f"[red]{error_msg}[/red]")
                console.print(
                    "Run [bold]arc build[/bold] to create the knowledge graph."
                )
            sys.exit(1)

        # Trace the history
        results = trace_history_for_file_line(
            db_path,
            file_path,
            line_number,
            max_results,
            max_hops
        )

        if not results:
            if format == Format.JSON:
                # For JSON format, return empty array
                print("[]")
            else:
                # For text format, use rich console
                console.print(
                    f"[yellow]No history found for {file_path}:{line_number}[/yellow]"
                )
            return

        # Output based on format
        if format == Format.JSON:
            # JSON output - print directly to stdout
            print(json.dumps(results))
        elif format == Format.MARKDOWN:
            # Markdown output
            md_content = f"# Decision Trail for {file_path}:{line_number}\n\n"
            
            for result in results:
                md_content += f"## {result['type'].capitalize()}: {result['title']}\n\n"
                md_content += f"**ID**: {result['id']}  \n"
                md_content += f"**Timestamp**: {result['timestamp'] or 'N/A'}  \n\n"
                
                # Add type-specific details
                if result["type"] == "commit":
                    if "author" in result:
                        md_content += f"**Author**: {result['author']}  \n"
                    if "sha" in result:
                        md_content += f"**SHA**: {result['sha']}  \n"
                elif result["type"] == "pr":
                    if "number" in result:
                        md_content += f"**PR**: #{result['number']}  \n"
                    if "state" in result:
                        md_content += f"**State**: {result['state']}  \n"
                    if "url" in result:
                        md_content += f"**URL**: {result['url']}  \n"
                elif result["type"] == "issue":
                    if "number" in result:
                        md_content += f"**Issue**: #{result['number']}  \n"
                    if "state" in result:
                        md_content += f"**State**: {result['state']}  \n"
                    if "url" in result:
                        md_content += f"**URL**: {result['url']}  \n"
                elif result["type"] == "adr":
                    if "status" in result:
                        md_content += f"**Status**: {result['status']}  \n"
                    if "decision_makers" in result:
                        decision_makers = result.get('decision_makers', [])
                        if not isinstance(decision_makers, list):
                            decision_makers = []
                        md_content += f"**Decision Makers**: {', '.join(decision_makers)}  \n"
                    if "path" in result:
                        md_content += f"**Path**: {result['path']}  \n"
                
                md_content += "\n---\n\n"
            
            # Print markdown
            console.print(Markdown(md_content))
        else:
            # Text output - use rich table and panels
            console.print(Panel(f"[bold]Decision Trail for {file_path}:{line_number}[/bold]", 
                               style="green"))
            
            for result in results:
                # Create a panel for each result
                title = f"[bold]{result['type'].upper()}[/bold]: {result['title']}"
                content = f"ID: {result['id']}\n"
                content += f"Timestamp: {result['timestamp'] or 'N/A'}\n\n"
                
                # Add type-specific details
                if result["type"] == "commit":
                    if "author" in result:
                        content += f"Author: {result['author']}\n"
                    if "sha" in result:
                        content += f"SHA: {result['sha']}"
                elif result["type"] == "pr":
                    if "number" in result:
                        content += f"PR #{result['number']}\n"
                    if "state" in result:
                        content += f"State: {result['state']}\n"
                    if "url" in result:
                        content += f"URL: {result['url']}"
                elif result["type"] == "issue":
                    if "number" in result:
                        content += f"Issue #{result['number']}\n"
                    if "state" in result:
                        content += f"State: {result['state']}\n"
                    if "url" in result:
                        content += f"URL: {result['url']}"
                elif result["type"] == "adr":
                    if "status" in result:
                        content += f"Status: {result['status']}\n"
                    if "decision_makers" in result:
                        content += f"Decision Makers: {', '.join(result['decision_makers'])}\n"
                    if "path" in result:
                        content += f"Path: {result['path']}"
                
                # Determine panel style based on node type
                style = {
                    "commit": "cyan",
                    "pr": "green",
                    "issue": "yellow",
                    "adr": "blue",
                    "file": "magenta"
                }.get(result["type"], "white")
                
                console.print(Panel(content, title=title, style=style))

    except Exception as e:
        logger.exception("Error in why_file command")
        error_msg = f"Error: {e}"
        if format == Format.JSON:
            # For JSON format, print errors to stderr
            print(error_msg, file=sys.stderr)
        else:
            # For text format, use rich console
            console.print(f"[red]{error_msg}[/red]")
        
        # Track error
        track_command_usage("why_file", success=False, error=e, context=context)
        sys.exit(1)


@app.command()
def query(
    question: str = typer.Argument(..., help="Natural language question to ask about the codebase"),
    max_results: int = typer.Option(
        5, "--max-results", "-m", help="Maximum number of results to return"
    ),
    depth: str = typer.Option(
        "medium", "--depth", "-d", 
        help="Search depth (shallow, medium, deep)"
    ),
    format: Format = typer.Option(
        Format.TEXT, "--format", "-f",
        help="Output format (text, json, or markdown)"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging"
    ),
) -> None:
    """Query the knowledge graph using natural language.

    This command allows you to ask questions about your codebase in natural language,
    leveraging the knowledge graph to provide rich, contextual answers about code history,
    decisions, and relationships.

    Examples:
        arc why query "Who implemented the authentication feature?"
        arc why query "Why was the database schema changed last month?"
        arc why query "What decision led to using SQLite instead of PostgreSQL?"
        arc why query "How has the API evolved since version 0.2.0?"
    """
    configure_logging(debug=debug)

    # Track command usage
    context = {
        "question": question,
        "max_results": max_results,
        "depth": depth,
        "format": format.value
    }
    track_command_usage("why_query", context=context)

    try:
        # Get the database path
        from arc_memory.sql.db import ensure_arc_dir
        arc_dir = ensure_arc_dir()
        db_path = arc_dir / "graph.db"

        # Check if the database exists
        if not db_path.exists():
            error_msg = f"Error: Database not found at {db_path}"
            if format == Format.JSON:
                # For JSON format, print errors to stderr
                print(error_msg, file=sys.stderr)
            else:
                # For text format, use rich console
                console.print(f"[red]{error_msg}[/red]")
                console.print(
                    "Run [bold]arc build[/bold] to create the knowledge graph."
                )
            sys.exit(1)

        # Import the natural language query processor
        from arc_memory.semantic_search import process_query
        
        # Process the natural language query
        console.print(Panel("[bold yellow]Processing your question...[/bold yellow]"))
        
        # Convert depth string to max_hops parameter
        max_hops = {
            "shallow": 2,
            "medium": 3,
            "deep": 4
        }.get(depth.lower(), 3)
        
        # Process the query and get results
        query_results = process_query(
            db_path,
            question,
            max_results=max_results,
            max_hops=max_hops
        )
        
        # Check for error in the results
        if "error" in query_results:
            error_msg = query_results["error"]
            if format == Format.JSON:
                # For JSON format, print errors as JSON
                print(json.dumps({"error": error_msg}))
            else:
                # For text format, use rich console
                console.print(f"[red]{error_msg}[/red]")
            return
        
        if not query_results or "results" not in query_results:
            if format == Format.JSON:
                # For JSON format, return empty object
                print("{}")
            else:
                # For text format, use rich console
                console.print(
                    "[yellow]No relevant information found for your question.[/yellow]"
                )
                console.print(
                    "Try rephrasing your question or using more specific terms."
                )
            return
        
        # Output based on format
        if format == Format.JSON:
            # JSON output - print directly to stdout
            print(json.dumps(query_results))
        elif format == Format.MARKDOWN:
            # Markdown output
            md_content = f"# Answer: {query_results.get('summary', 'No summary available')}\n\n"
            
            # Add understanding section
            if "understanding" in query_results:
                md_content += f"## Query Understanding\n\n{query_results['understanding']}\n\n"
            
            # Add main answer
            if "answer" in query_results:
                md_content += f"## Detailed Answer\n\n{query_results['answer']}\n\n"
            
            # Add supporting evidence
            if "results" in query_results and query_results["results"]:
                md_content += "## Supporting Evidence\n\n"
                
                for result in query_results["results"]:
                    md_content += f"### {result['type'].capitalize()}: {result['title']}\n\n"
                    md_content += f"**ID**: {result['id']}  \n"
                    if "timestamp" in result:
                        md_content += f"**Timestamp**: {result.get('timestamp') or 'N/A'}  \n"
                    if "relevance" in result:
                        md_content += f"**Relevance**: {result.get('relevance')}  \n"
                    
                    # Add type-specific details
                    if result["type"] == "commit":
                        if "author" in result:
                            md_content += f"**Author**: {result.get('author')}  \n"
                        if "sha" in result:
                            md_content += f"**SHA**: {result.get('sha')}  \n"
                    elif result["type"] == "pr":
                        if "number" in result:
                            md_content += f"**PR**: #{result.get('number')}  \n"
                        if "state" in result:
                            md_content += f"**State**: {result.get('state')}  \n"
                        if "url" in result:
                            md_content += f"**URL**: {result.get('url')}  \n"
                    elif result["type"] == "issue":
                        if "number" in result:
                            md_content += f"**Issue**: #{result.get('number')}  \n"
                        if "state" in result:
                            md_content += f"**State**: {result.get('state')}  \n"
                        if "url" in result:
                            md_content += f"**URL**: {result.get('url')}  \n"
                    elif result["type"] == "adr":
                        if "status" in result:
                            md_content += f"**Status**: {result.get('status')}  \n"
                        if "decision_makers" in result:
                            decision_makers = result.get('decision_makers', [])
                            if not isinstance(decision_makers, list):
                                decision_makers = []
                            md_content += f"**Decision Makers**: {', '.join(decision_makers)}  \n"
                        if "path" in result:
                            md_content += f"**Path**: {result.get('path')}  \n"
                    
                    # Add reasoning if available
                    if "reasoning" in result:
                        md_content += f"\n{result.get('reasoning')}  \n"
                    
                    md_content += "\n---\n\n"
            
            # Add confidence level
            if "confidence" in query_results:
                md_content += f"## Confidence\n\n{query_results['confidence']}/10\n\n"
            
            # Print markdown
            console.print(Markdown(md_content))
        else:
            # Text output - use rich panels
            # Main answer panel
            summary = query_results.get("summary", "No summary available")
            console.print(Panel(f"[bold]{summary}[/bold]", 
                              title="[bold green]Answer[/bold green]", 
                              style="green"))
            
            # Query understanding panel
            if "understanding" in query_results:
                console.print(Panel(query_results["understanding"], 
                                 title="[bold blue]Query Understanding[/bold blue]", 
                                 style="blue"))
            
            # Detailed answer panel
            if "answer" in query_results:
                console.print(Panel(query_results["answer"], 
                                 title="[bold yellow]Detailed Answer[/bold yellow]", 
                                 style="yellow"))
            
            # Supporting evidence
            if "results" in query_results and query_results["results"]:
                console.print("\n[bold]Supporting Evidence:[/bold]")
                
                for result in query_results["results"]:
                    # Create a panel for each result
                    title = f"[bold]{result['type'].upper()}[/bold]: {result['title']}"
                    content = f"ID: {result['id']}\n"
                    if "timestamp" in result:
                        content += f"Timestamp: {result['timestamp'] or 'N/A'}\n"
                    if "relevance" in result:
                        content += f"Relevance: {result['relevance']}\n\n"
                    
                    # Add type-specific details
                    if result["type"] == "commit":
                        if "author" in result:
                            content += f"Author: {result['author']}\n"
                        if "sha" in result:
                            content += f"SHA: {result['sha']}\n"
                    elif result["type"] == "pr":
                        if "number" in result:
                            content += f"PR #{result['number']}\n"
                        if "state" in result:
                            content += f"State: {result['state']}\n"
                        if "url" in result:
                            content += f"URL: {result['url']}\n"
                    elif result["type"] == "issue":
                        if "number" in result:
                            content += f"Issue #{result['number']}\n"
                        if "state" in result:
                            content += f"State: {result['state']}\n"
                        if "url" in result:
                            content += f"URL: {result['url']}\n"
                    elif result["type"] == "adr":
                        if "status" in result:
                            content += f"Status: {result['status']}\n"
                        if "decision_makers" in result:
                            content += f"Decision Makers: {', '.join(result['decision_makers'])}\n"
                        if "path" in result:
                            content += f"Path: {result['path']}\n"
                    
                    # Add reasoning if available
                    if "reasoning" in result:
                        content += f"\n{result['reasoning']}"
                    
                    # Determine panel style based on node type
                    style = {
                        "commit": "cyan",
                        "pr": "green",
                        "issue": "yellow",
                        "adr": "blue",
                        "file": "magenta"
                    }.get(result["type"], "white")
                    
                    console.print(Panel(content, title=title, style=style))
            
            # Confidence level
            if "confidence" in query_results:
                console.print(f"\n[bold]Confidence:[/bold] {query_results['confidence']}/10")

    except Exception as e:
        logger.exception("Error in why_query command")
        error_msg = f"Error: {e}"
        if format == Format.JSON:
            # For JSON format, print errors to stderr
            print(error_msg, file=sys.stderr)
        else:
            # For text format, use rich console
            console.print(f"[red]{error_msg}[/red]")
        
        # Track error
        track_command_usage("why_query", success=False, error=e, context=context)
        sys.exit(1)
