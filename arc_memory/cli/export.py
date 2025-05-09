"""Export command for Arc Memory CLI.

This command exports a relevant slice of the knowledge graph as a JSON file
for use in GitHub App PR review workflows.
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from arc_memory.errors import ExportError
from arc_memory.export import export_graph
from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.sql.db import ensure_arc_dir
from arc_memory.telemetry import track_cli_command

console = Console()
logger = get_logger(__name__)


def export(
    pr: str = typer.Argument(
        ..., help="SHA of the PR head commit"
    ),
    out: Path = typer.Argument(
        ..., help="Output file path for the JSON"
    ),
    compress: bool = typer.Option(
        True, help="Compress the output file"
    ),
    sign: bool = typer.Option(
        False, help="Sign the output file with GPG"
    ),
    key: Optional[str] = typer.Option(
        None, help="GPG key ID to use for signing"
    ),
    repo_path: Optional[Path] = typer.Option(
        None, "--repo", help="Path to the Git repository"
    ),
    db_path: Optional[Path] = typer.Option(
        None, "--db", help="Path to the database file"
    ),
    base_branch: str = typer.Option(
        "main", "--base", help="Base branch to compare against"
    ),
    max_hops: int = typer.Option(
        3, "--max-hops", help="Maximum number of hops to traverse in the graph"
    ),
    enhance_for_llm: bool = typer.Option(
        True, "--enhance-for-llm/--no-enhance-for-llm",
        help="Enhance the export data for LLM reasoning"
    ),
    include_causal: bool = typer.Option(
        True, "--include-causal/--no-causal",
        help="Include causal relationships in the export"
    ),
    ci_mode: bool = typer.Option(
        False, "--ci-mode", help="Optimize for CI environments"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging"
    ),
) -> None:
    """Export a relevant slice of the knowledge graph for PR review.

    This command exports a subset of the knowledge graph focused on the files
    modified in a specific PR, along with related nodes and edges. The export
    is saved as a JSON file that can be used by the GitHub App for PR reviews.

    The export includes:
    - Modified files and their relationships
    - Related entities (commits, PRs, issues, etc.)
    - Causal relationships (decisions, implications, code changes)
    - Reasoning structures from the Knowledge Graph of Thoughts

    Examples:
        arc export abc123 --out arc-graph.json
        arc export abc123 --out arc-graph.json.gz --compress
        arc export abc123 --out arc-graph.json --sign --key ABCD1234
        arc export abc123 --out arc-graph.json --max-hops 3
        arc export abc123 --out arc-graph.json --no-enhance-for-llm
        arc export abc123 --out arc-graph.json --no-causal
    """
    configure_logging(debug=debug or is_debug_mode())

    # Track command usage
    args = {
        "pr": pr,
        "compress": compress,
        "sign": sign,
        "base_branch": base_branch,
        "max_hops": max_hops,
        "enhance_for_llm": enhance_for_llm,
        "include_causal": include_causal,
        "ci_mode": ci_mode,
        "debug": debug,
    }
    track_cli_command("export", args=args)

    try:
        # Determine repository path
        if repo_path is None:
            repo_path = Path.cwd()

        # Determine database path
        if db_path is None:
            arc_dir = ensure_arc_dir()
            db_path = arc_dir / "graph.db"

        # Check if the database exists
        if not db_path.exists():
            error_msg = f"Error: Database not found at {db_path}"
            console.print(f"[red]{error_msg}[/red]")
            console.print(
                "Run [bold]arc build[/bold] to create the knowledge graph."
            )
            sys.exit(1)

        # Export the graph
        console.print(f"Exporting graph for PR [bold]{pr}[/bold]...")

        output_path = export_graph(
            db_path=db_path,
            repo_path=repo_path,
            pr_sha=pr,
            output_path=out,
            compress=compress,
            sign=sign,
            key_id=key,
            base_branch=base_branch,
            max_hops=max_hops,
            enhance_for_llm=enhance_for_llm,
            include_causal=include_causal,
        )

        console.print(f"[green]Export complete! Saved to {output_path}[/green]")

        # If signed, show the signature file
        if sign and Path(str(output_path) + '.sig').exists():
            sig_path = Path(str(output_path) + '.sig')
            console.print(f"[green]Signature saved to {sig_path}[/green]")

    except ExportError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error in export command")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)
