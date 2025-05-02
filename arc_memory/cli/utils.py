"""Utility functions for the CLI.

This module provides utility functions for the CLI, including formatting
functions for simulation results.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn


def format_date(date_str: str) -> str:
    """Format a date string for display.
    
    Args:
        date_str: Date string in ISO format
        
    Returns:
        Formatted date string
    """
    try:
        if not date_str or date_str == "unknown":
            return "Unknown"
        
        # Try to parse as ISO format
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return date_str


def format_metrics(metrics: Dict[str, Any]) -> str:
    """Format metrics for display.
    
    Args:
        metrics: Dictionary of metrics
        
    Returns:
        Formatted metrics string in markdown format
    """
    if not metrics:
        return "No metrics available"
    
    result = []
    
    # Format simple metrics first
    for key, value in metrics.items():
        if not isinstance(value, dict):
            # Format the key for better readability
            display_key = key.replace("_", " ").title()
            
            # Format the value based on its type
            if isinstance(value, float):
                display_value = f"{value:.4f}"
            elif isinstance(value, bool):
                display_value = "Yes" if value else "No"
            else:
                display_value = str(value)
                
            result.append(f"- **{display_key}**: {display_value}")
    
    # Format nested metrics
    for key, value in metrics.items():
        if isinstance(value, dict):
            result.append(f"\n### {key.replace('_', ' ').title()}")
            for sub_key, sub_value in value.items():
                display_sub_key = sub_key.replace("_", " ").title()
                
                if isinstance(sub_value, float):
                    display_sub_value = f"{sub_value:.4f}"
                elif isinstance(sub_value, bool):
                    display_sub_value = "Yes" if sub_value else "No"
                else:
                    display_sub_value = str(sub_value)
                    
                result.append(f"- **{display_sub_key}**: {display_sub_value}")
    
    return "\n".join(result)


def format_simulation_results(results: Dict[str, Any]) -> str:
    """Convert simulation results to human-readable markdown.
    
    Args:
        results: Simulation results dictionary
        
    Returns:
        Markdown formatted string
    """
    # Extract data from results
    sim_id = results.get("sim_id", "Unknown")
    risk_score = results.get("risk_score", 0)
    services = results.get("services", [])
    metrics = results.get("metrics", {})
    explanation = results.get("explanation", "No explanation available")
    timestamp = format_date(results.get("timestamp", ""))
    scenario = results.get("scenario", "Unknown").replace("_", " ").title()
    
    # Format risk level based on score
    risk_level = "Low"
    if risk_score >= 75:
        risk_level = "Critical"
    elif risk_score >= 50:
        risk_level = "High"
    elif risk_score >= 25:
        risk_level = "Medium"
    
    # Format services list
    services_str = ", ".join(services) if services else "None"
    
    # Extract simulation log summary if available
    log_summary = results.get("simulation_log_summary", {})
    log_summary_str = ""
    if log_summary:
        log_summary_str = f"""
## Simulation Log Summary
- **Duration**: {log_summary.get("duration", 0):.2f} seconds
- **Total Commands**: {log_summary.get("total_commands", 0)}
- **Total Metrics Collected**: {log_summary.get("total_metrics", 0)}
- **Total Errors**: {log_summary.get("total_errors", 0)}
"""
    
    # Extract command logs if available
    command_logs = results.get("command_logs", [])
    command_logs_str = ""
    if command_logs:
        # Only show a subset of commands to avoid overwhelming the output
        sample_commands = command_logs[:3]
        if len(command_logs) > 3:
            sample_commands.append(command_logs[-1])
        
        command_logs_str = f"""
## Command Execution Summary
Total commands executed: {len(command_logs)}

Sample of commands:
"""
        for i, cmd in enumerate(sample_commands):
            if isinstance(cmd, dict):
                success = cmd.get("success", False)
                status = "✅ Success" if success else "❌ Failed"
                description = cmd.get("description", "Unknown")
                command = cmd.get("command", [])
                if isinstance(command, list):
                    command = " ".join(command)
                returncode = cmd.get("returncode", "N/A")
                
                command_logs_str += f"""
### Command {i+1}: {description}
- **Status**: {status} (Exit code: {returncode})
- **Command**: `{command}`
"""
                # Add truncated output if available
                stdout = cmd.get("stdout", "")
                if stdout and len(stdout) > 100:
                    stdout = stdout[:100] + "..."
                if stdout:
                    command_logs_str += f"- **Output**: ```\n{stdout}\n```\n"
        
        if len(command_logs) > 4:
            command_logs_str += f"\n*...and {len(command_logs) - 4} more commands (use --verbose for full details)*"
    
    # Extract detailed log path if available
    detailed_log_path = results.get("detailed_log_path", "")
    detailed_log_str = ""
    if detailed_log_path:
        detailed_log_str = f"""
## Detailed Logs
Full simulation logs are available at: `{detailed_log_path}`
"""
    
    # Build the markdown
    markdown = f"""
# Simulation Results: {sim_id}

## Summary
- **Date**: {timestamp}
- **Scenario**: {scenario}
- **Risk Score**: {risk_score}/100 ({risk_level} Risk)
- **Affected Services**: {services_str}

## Detailed Analysis
{explanation}

## Metrics
{format_metrics(metrics)}
{log_summary_str}
{command_logs_str}
{detailed_log_str}
"""
    
    return markdown


def display_simulation_results(results: Dict[str, Any], console: Console, verbose: bool = False) -> None:
    """Display simulation results in the console.
    
    Args:
        results: Simulation results dictionary
        console: Rich console for output
        verbose: Whether to display verbose output
    """
    # Convert results to markdown
    markdown_str = format_simulation_results(results)
    
    # Display using Rich's Markdown renderer
    console.print(Markdown(markdown_str))
    
    # If verbose mode is enabled and command logs are available, show more details
    if verbose and "command_logs" in results:
        command_logs = results.get("command_logs", [])
        if command_logs:
            console.print("\n[bold]Detailed Command Execution Log:[/bold]")
            
            # Create a table for command logs
            from rich.table import Table
            table = Table(title="Command Execution Details")
            table.add_column("Command #", style="cyan")
            table.add_column("Description", style="green")
            table.add_column("Status", style="bold")
            table.add_column("Duration", style="magenta")
            
            for i, cmd in enumerate(command_logs):
                if isinstance(cmd, dict):
                    success = cmd.get("success", False)
                    status = "[green]Success[/green]" if success else "[red]Failed[/red]"
                    description = cmd.get("description", "Unknown")
                    duration = cmd.get("duration", 0)
                    
                    table.add_row(
                        str(i+1),
                        description,
                        status,
                        f"{duration:.2f}s"
                    )
            
            console.print(table)


def create_progress_display() -> Progress:
    """Create a progress display for long-running operations.
    
    Returns:
        Rich Progress object
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=Console(),
        transient=True
    )
