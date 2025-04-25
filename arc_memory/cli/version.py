"""Version command for Arc Memory CLI."""

import typer
from rich.console import Console

import arc_memory

app = typer.Typer(help="Show version information")
console = Console()


@app.callback(invoke_without_command=True)
def callback() -> None:
    """Show the version of Arc Memory."""
    console.print(f"Arc Memory version: {arc_memory.__version__}")
