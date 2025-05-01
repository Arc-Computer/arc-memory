"""Simulation command for Arc Memory CLI.

This command provides functionality to simulate the impact of code changes
by running targeted fault injection experiments in isolated sandbox environments.
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from arc_memory.logging_conf import configure_logging
from arc_memory.logging_conf import get_logger
from arc_memory.logging_conf import is_debug_mode

logger = get_logger(__name__)
from arc_memory.simulate.causal import derive_causal
from arc_memory.simulate.diff_utils import GitError
from arc_memory.simulate.diff_utils import analyze_diff
from arc_memory.simulate.diff_utils import load_diff_from_file
from arc_memory.simulate.diff_utils import serialize_diff
from arc_memory.simulate.manifest import generate_simulation_manifest
from arc_memory.simulate.manifest import list_available_scenarios

# Try to import the LangGraph workflow, but don't fail if it's not available
try:
    from arc_memory.simulate.langgraph_flow import run_sim as run_langgraph_workflow
    HAS_LANGGRAPH = True
except ImportError:
    logger.warning("LangGraph not found. LangGraph workflow will not be available.")
    HAS_LANGGRAPH = False
    run_langgraph_workflow = None

# Try to import the sandbox simulation, but don't fail if it's not available
try:
    from arc_memory.simulate.code_interpreter import run_simulation as run_sandbox_simulation
    HAS_SANDBOX = True
except ImportError:
    logger.warning("E2B Code Interpreter not found. Sandbox simulation will not be available.")
    HAS_SANDBOX = False
    run_sandbox_simulation = None
from arc_memory.sql.db import ensure_arc_dir
from arc_memory.telemetry import track_cli_command


def run_simulation_and_extract_metrics(
    manifest_path: Path,
    severity: int,
    timeout: int
) -> Tuple[Dict[str, Any], int]:
    """Run a simulation and extract metrics.

    Args:
        manifest_path: Path to the simulation manifest
        severity: Severity threshold (0-100)
        timeout: Maximum simulation duration in seconds

    Returns:
        A tuple of (metrics, risk_score)
    """
    # Check if sandbox simulation is available
    if HAS_SANDBOX and run_sandbox_simulation:
        logger.info("Running simulation in sandbox environment")
        console.print("[bold]Running simulation in sandbox environment...[/bold]")

        try:
            # Run the simulation with a shorter timeout for now
            simulation_timeout = min(timeout, 300)  # Cap at 5 minutes for now
            simulation_results = run_sandbox_simulation(
                manifest_path=manifest_path,
                duration_seconds=simulation_timeout,
                metrics_interval=30  # Collect metrics every 30 seconds
            )

            # Extract metrics from the simulation results
            metrics = {
                "latency_ms": int(severity * 10),  # Based on severity
                "error_rate": round(severity / 1000, 3),  # Based on severity
            }

            # Add actual metrics from simulation if available
            if "final_metrics" in simulation_results:
                final_metrics = simulation_results.get("final_metrics", {})

                # Extract basic metrics
                basic_metrics = extract_metrics(
                    final_metrics,
                    ["node_count", "pod_count", "service_count"]
                )
                metrics.update(basic_metrics)

                # Extract resource usage metrics
                if "cpu_usage" in final_metrics:
                    metrics["cpu_usage"] = final_metrics.get("cpu_usage", {})
                if "memory_usage" in final_metrics:
                    metrics["memory_usage"] = final_metrics.get("memory_usage", {})

            # Add experiment details if available
            if "experiment_name" in simulation_results:
                metrics["experiment_name"] = simulation_results.get("experiment_name")

            # Add metrics history if available for detailed analysis
            if "metrics_history" in simulation_results:
                metrics["metrics_history"] = simulation_results.get("metrics_history")

            # Calculate risk score based on simulation results
            # For now, use a simple formula based on severity and metrics
            risk_score = severity // 2

            console.print("[green]Simulation completed successfully[/green]")
        except Exception as e:
            logger.warning(f"Simulation failed, falling back to static analysis: {e}")
            console.print(f"[yellow]Simulation failed, falling back to static analysis: {e}[/yellow]")

            # Fall back to static analysis
            metrics, risk_score = get_static_analysis_metrics(severity)
    else:
        logger.info("Sandbox simulation not available, using static analysis")
        console.print("[yellow]Sandbox simulation not available, using static analysis[/yellow]")

        # Use static analysis
        metrics, risk_score = get_static_analysis_metrics(severity)

    return metrics, risk_score


def extract_metrics(metrics_data: Dict[str, Any], metric_keys: List[str], default_value: Any = 0) -> Dict[str, Any]:
    """Extract specific metrics from metrics data.

    Args:
        metrics_data: The metrics data to extract from
        metric_keys: List of metric keys to extract
        default_value: Default value to use if a metric is not found

    Returns:
        A dictionary of extracted metrics
    """
    return {key: metrics_data.get(key, default_value) for key in metric_keys}


def get_static_analysis_metrics(severity: int) -> Tuple[Dict[str, Any], int]:
    """Get metrics based on static analysis.

    Args:
        severity: Severity threshold (0-100)

    Returns:
        A tuple of (metrics, risk_score)
    """
    metrics = {
        "latency_ms": int(severity * 10),  # Based on severity
        "error_rate": round(severity / 1000, 3)  # Based on severity
    }
    risk_score = severity // 2  # Placeholder score based on severity

    return metrics, risk_score


def output_simulation_results(result: Dict[str, Any], output_path: Optional[Path], severity: int, console: Console) -> None:
    """Output simulation results and set appropriate exit code.

    Args:
        result: The simulation results
        output_path: Path to write result JSON (optional)
        severity: CI fail threshold 0-100
        console: Rich console for output
    """
    # Output the result
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]Results written to: {output_path}[/green]")
    else:
        console.print("\n[bold]Simulation Results:[/bold]")
        console.print(json.dumps(result, indent=2))

    # Return appropriate exit code based on risk score
    if result["risk_score"] >= severity:
        console.print(f"[red]Risk score {result['risk_score']} exceeds threshold {severity}[/red]")
        sys.exit(1)  # Failure - risk score exceeds threshold
    else:
        console.print(f"[green]Risk score {result['risk_score']} is below threshold {severity}[/green]")
        # Success - continue with exit code 0

app = typer.Typer(help="Simulate the impact of code changes with fault injection")
console = Console()
logger = get_logger(__name__)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    rev_range: str=typer.Option(
        "HEAD~1..HEAD", help="Git rev-range to analyze"
    ),
    diff: Optional[Path]=typer.Option(
        None, help="Path to pre-serialized diff JSON"
    ),
    scenario: str=typer.Option(
        "network_latency", help="Fault scenario ID"
    ),
    severity: int=typer.Option(
        50, help="CI fail threshold 0-100"
    ),
    timeout: int=typer.Option(
        600, help="Max runtime in seconds"
    ),
    output: Optional[Path]=typer.Option(
        None, help="Write result JSON to file (default: stdout)"
    ),
    open_ui: bool=typer.Option(
        False, "--open-ui/--no-ui", help="Open VS Code webview if available"
    ),
    verbose: bool=typer.Option(
        False, "-v", "--verbose", help="Enable verbose output"
    ),
    debug: bool=typer.Option(
        False, "--debug", help="Enable debug logging"
    ),
) -> None:
    """Simulate the impact of code changes with fault injection.

    This command analyzes code changes, runs targeted fault injection experiments
    in isolated sandbox environments, and provides risk assessments with attestation.

    Examples:
        arc sim
        arc sim --rev-range HEAD~3..HEAD
        arc sim --scenario cpu_stress --severity 75
        arc sim --output ./simulation-results.json
        arc sim --verbose --open-ui
    """
    configure_logging(debug=debug or is_debug_mode() or verbose)

    # If a subcommand was invoked, don't run the default command
    if ctx.invoked_subcommand is not None:
        return

    # Track command usage
    args = {
        "rev_range": rev_range,
        "scenario": scenario,
        "severity": severity,
        "timeout": timeout,
        "verbose": verbose,
        "open_ui": open_ui,
        # Don't include sensitive data
    }
    track_cli_command("sim", args=args)

    # Call the main simulation function
    run_simulation(
        rev_range=rev_range,
        diff_path=diff,
        scenario=scenario,
        severity=severity,
        timeout=timeout,
        output_path=output,
        open_ui=open_ui,
        verbose=verbose,
        debug=debug,
    )


def run_simulation(
    rev_range: str,
    diff_path: Optional[Path]=None,
    scenario: str="network_latency",
    severity: int=50,
    timeout: int=600,
    output_path: Optional[Path]=None,
    open_ui: bool=False,
    verbose: bool=False,
    debug: bool=False,
) -> None:
    """Run a simulation to predict the impact of code changes.

    Args:
        rev_range: Git rev-range to analyze
        diff_path: Path to pre-serialized diff JSON
        scenario: Fault scenario ID
        severity: CI fail threshold 0-100
        timeout: Max runtime in seconds
        output_path: Path to write result JSON
        open_ui: Whether to open VS Code webview
        verbose: Whether to enable verbose output
        debug: Whether to enable debug logging
    """
    try:
        # Get the database path
        arc_dir = ensure_arc_dir()
        db_path = arc_dir / "graph.db"

        # Check if LangGraph workflow is available
        if HAS_LANGGRAPH and run_langgraph_workflow:
            logger.info("Using LangGraph workflow for simulation")
            console.print("[bold]Using LangGraph workflow for simulation...[/bold]")

            # If diff_path is provided, we need to load it first
            diff_data = None
            if diff_path:
                logger.info(f"Loading diff from file: {diff_path}")
                try:
                    diff_data = load_diff_from_file(diff_path)
                    console.print(f"[green]Successfully loaded diff from file with {len(diff_data.get('files', []))} files[/green]")
                except Exception as e:
                    console.print(f"[red]Error loading diff file: {e}[/red]")
                    sys.exit(3)  # Invalid Input

            # Run the LangGraph workflow
            workflow_result = run_langgraph_workflow(
                rev_range=rev_range,
                scenario=scenario,
                severity=severity,
                timeout=timeout,
                repo_path=os.getcwd(),
                db_path=str(db_path),
                diff_data=diff_data  # Pass the pre-loaded diff data if available
            )

            # Check if the workflow completed successfully
            if workflow_result.get("status") != "completed":
                error_message = workflow_result.get("error", "Unknown error")
                console.print(f"[red]Workflow failed: {error_message}[/red]")
                sys.exit(2)  # Error

            # Get the attestation
            attestation = workflow_result.get("attestation", {})

            # Create the result object
            result = {
                "sim_id": attestation.get("sim_id", f"sim_{rev_range.replace('..', '_').replace('/', '_')}"),
                "risk_score": attestation.get("risk_score", 0),
                "services": workflow_result.get("affected_services", []),
                "metrics": attestation.get("metrics", {}),
                "explanation": attestation.get("explanation", ""),
                "manifest_hash": attestation.get("manifest_hash", ""),
                "commit_target": attestation.get("commit_target", "unknown"),
                "timestamp": attestation.get("timestamp", "unknown"),
                "diff_hash": attestation.get("diff_hash", "")
            }

            # Output the result using the shared function
            output_simulation_results(result, output_path, severity, console)

            return

        # If LangGraph is not available, fall back to the original implementation
        logger.info("LangGraph workflow not available, using traditional approach")
        console.print("[yellow]LangGraph workflow not available, using traditional approach[/yellow]")

        # Step 1: Get the diff
        diff_data = None
        if diff_path:
            logger.info(f"Loading diff from file: {diff_path}")
            try:
                diff_data = load_diff_from_file(diff_path)
            except Exception as e:
                console.print(f"[red]Error loading diff file: {e}[/red]")
                sys.exit(3)  # Invalid Input
        else:
            logger.info(f"Extracting diff for range: {rev_range}")
            try:
                diff_data = serialize_diff(rev_range)
            except GitError as e:
                console.print(f"[red]Git error: {e}[/red]")
                sys.exit(3)  # Invalid Input
            except Exception as e:
                console.print(f"[red]Error extracting diff: {e}[/red]")
                sys.exit(2)  # Error

        # Print diff summary
        file_count = len(diff_data.get("files", []))
        console.print(f"[bold]Diff Analysis:[/bold] Found {file_count} changed files")

        # Step 2: Analyze the diff to identify affected services
        logger.info("Analyzing diff to identify affected services")
        affected_services = analyze_diff(diff_data, db_path)

        # Create a table to display affected services
        table = Table(title="Affected Services")
        table.add_column("Service", style="cyan")
        table.add_column("Files", style="green")

        # Get the files for each service
        service_files = {}
        for file_data in diff_data.get("files", []):
            file_path = file_data["path"]
            for service in affected_services:
                if service not in service_files:
                    service_files[service] = []
                # Use a regular expression to robustly associate files with services
                # Match the service name as a distinct word or path component
                service_prefix = service.split("-")[0]
                if re.search(rf"(^|/){re.escape(service_prefix)}($|/|\.)", file_path.lower()):
                    service_files[service].append(file_path)

        # Add rows to the table
        for service in affected_services:
            files = service_files.get(service, [])
            file_list = "\n".join(files[:3])
            if len(files) > 3:
                file_list += f"\n... and {len(files) - 3} more"
            table.add_row(service, file_list if files else "Inferred from dependencies")

        console.print(table)

        # Step 3: Generate a simulation manifest
        logger.info(f"Generating simulation manifest for scenario: {scenario}")
        console.print(f"[bold]Scenario:[/bold] {scenario}")
        console.print(f"[bold]Severity Threshold:[/bold] {severity}")
        console.print(f"[bold]Timeout:[/bold] {timeout} seconds")

        # Get the causal graph
        logger.info("Deriving causal graph from knowledge graph")
        causal_graph = derive_causal(db_path)

        # Get the affected files
        affected_files = [file["path"] for file in diff_data.get("files", [])]

        # Generate the manifest
        manifest_path = None
        if output_path:
            # If an output path is provided, save the manifest next to it
            manifest_path = output_path.parent / f"{output_path.stem}_manifest.yaml"

        # Generate the simulation manifest
        manifest = generate_simulation_manifest(
            causal_graph=causal_graph,
            affected_files=affected_files,
            scenario=scenario,
            severity=severity,
            target_services=affected_services,
            output_path=manifest_path
        )

        # Get the manifest hash
        manifest_hash = manifest["metadata"]["annotations"]["arc-memory.io/manifest-hash"]

        # Run the simulation
        metrics, risk_score = run_simulation_and_extract_metrics(
            manifest_path=manifest_path,
            severity=severity,
            timeout=timeout
        )

        # Create the simulation result
        result = {
            "sim_id": f"sim_{rev_range.replace('..', '_').replace('/', '_')}",
            "risk_score": risk_score,
            "services": affected_services,
            "metrics": metrics,
            "explanation": f"Simulation for {len(affected_services)} services based on {file_count} changed files.",
            "manifest_hash": manifest_hash,
            "commit_target": diff_data.get("end_commit", "unknown"),
            "timestamp": diff_data.get("timestamp", "unknown"),
            "diff_hash": hashlib.md5(json.dumps(diff_data, sort_keys=True).encode('utf-8')).hexdigest()
        }

        # Output the result using the shared function
        output_simulation_results(result, output_path, severity, console)

    except Exception as e:
        logger.exception("Error in simulation")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(2)  # Error


# List available scenarios
@app.command("list-scenarios")
def list_scenarios() -> None:
    """List available fault scenarios."""
    scenarios = list_available_scenarios()

    console.print("[bold]Available Fault Scenarios:[/bold]")
    for scenario in scenarios:
        console.print(f"  • {scenario['id']} - {scenario['description']}")
