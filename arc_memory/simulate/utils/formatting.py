"""Formatting utilities for Arc Memory simulation.

This module provides utilities for formatting simulation results.
"""

import json
from typing import Dict, List, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def format_simulation_results(results: Dict[str, Any], format_type: str = "markdown") -> str:
    """Format simulation results for display.
    
    Args:
        results: Simulation results
        format_type: Output format type (markdown, json, text)
        
    Returns:
        Formatted simulation results
    """
    if format_type == "json":
        return json.dumps(results, indent=2)
    
    if format_type == "markdown":
        return format_simulation_results_markdown(results)
    
    # Default to text format
    return format_simulation_results_text(results)


def format_simulation_results_markdown(results: Dict[str, Any]) -> str:
    """Format simulation results as markdown.
    
    Args:
        results: Simulation results
        
    Returns:
        Markdown-formatted simulation results
    """
    # Extract key information
    status = results.get("status", "unknown")
    risk_score = results.get("risk_score", 0)
    affected_services = results.get("affected_services", [])
    explanation = results.get("explanation", "No explanation available.")
    
    # Format the markdown
    markdown = f"""
# Simulation Results

## Summary
- **Status**: {status}
- **Risk Score**: {risk_score}/100
- **Affected Services**: {", ".join(affected_services) if affected_services else "None"}

## Explanation
{explanation}
"""
    
    # Add metrics if available
    if "metrics" in results:
        markdown += "\n## Metrics\n"
        for key, value in results["metrics"].items():
            if isinstance(value, dict):
                markdown += f"### {key}\n"
                for subkey, subvalue in value.items():
                    markdown += f"- **{subkey}**: {subvalue}\n"
            else:
                markdown += f"- **{key}**: {value}\n"
    
    return markdown


def format_simulation_results_text(results: Dict[str, Any]) -> str:
    """Format simulation results as plain text.
    
    Args:
        results: Simulation results
        
    Returns:
        Text-formatted simulation results
    """
    # Extract key information
    status = results.get("status", "unknown")
    risk_score = results.get("risk_score", 0)
    affected_services = results.get("affected_services", [])
    explanation = results.get("explanation", "No explanation available.")
    
    # Format the text
    text = f"""
Simulation Results
=================

Summary:
- Status: {status}
- Risk Score: {risk_score}/100
- Affected Services: {", ".join(affected_services) if affected_services else "None"}

Explanation:
{explanation}
"""
    
    # Add metrics if available
    if "metrics" in results:
        text += "\nMetrics:\n"
        for key, value in results["metrics"].items():
            if isinstance(value, dict):
                text += f"{key}:\n"
                for subkey, subvalue in value.items():
                    text += f"  - {subkey}: {subvalue}\n"
            else:
                text += f"- {key}: {value}\n"
    
    return text


def create_rich_table(title: str, columns: List[str], rows: List[List[str]]) -> Table:
    """Create a Rich table for display.
    
    Args:
        title: Table title
        columns: Column names
        rows: Table rows
        
    Returns:
        A Rich table
    """
    table = Table(title=title)
    
    # Add columns
    for column in columns:
        table.add_column(column)
    
    # Add rows
    for row in rows:
        table.add_row(*row)
    
    return table
