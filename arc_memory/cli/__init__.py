"""Command-line interface for Arc Memory."""

import typer
from rich.console import Console

import arc_memory

app = typer.Typer(
    name="arc",
    help="Arc Memory - Local bi-temporal knowledge graph for code repositories.",
    add_completion=False,
)

console = Console()

# Import commands to register them with the app
from arc_memory.cli.auth import app as auth_app
from arc_memory.cli.build import build as build_command
from arc_memory.cli.doctor import app as doctor_app
from arc_memory.cli.export import export as export_command
from arc_memory.cli.migrate import app as migrate_app
from arc_memory.cli.refresh import app as refresh_app
from arc_memory.cli.trace import app as trace_app
from arc_memory.cli.why import app as why_app
from arc_memory.cli.relate import app as relate_app
from arc_memory.cli.serve import app as serve_app

# Add commands to the main app
app.add_typer(auth_app, name="auth")
app.command()(build_command)  # Add build command directly
app.add_typer(doctor_app, name="doctor")
app.add_typer(migrate_app, name="migrate")
app.add_typer(refresh_app, name="refresh")
app.add_typer(trace_app, name="trace")
app.add_typer(why_app, name="why")
app.add_typer(relate_app, name="relate")
app.add_typer(serve_app, name="serve")

# Add export command directly to the main app
app.command()(export_command)

@app.command()
def version():
    """Show the version of Arc Memory."""
    console.print(f"Arc Memory version: {arc_memory.__version__}")
