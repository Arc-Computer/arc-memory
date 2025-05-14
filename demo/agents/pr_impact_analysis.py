#!/usr/bin/env python3
"""
PR Impact Analysis Demo

This script analyzes the potential impact of a PR by examining the files changed
and predicting which components might be affected by the changes.

Usage:
    python pr_impact_analysis.py <pr_number>

Example:
    python pr_impact_analysis.py 71
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
import colorama
from colorama import Fore, Style

# Suppress OpenAI debug logs
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("arc_memory.llm.openai_client").setLevel(logging.WARNING)

# Initialize colorama for cross-platform colored terminal output
colorama.init()

try:
    from arc_memory.sdk import Arc
except ImportError:
    print(f"{Fore.RED}Error: Arc Memory SDK not found. Please install it with 'pip install arc-memory'.{Style.RESET_ALL}")
    sys.exit(1)

def analyze_pr_impact(repo_path, pr_number):
    """
    Analyze the potential impact of a PR.

    Args:
        repo_path: Path to the repository
        pr_number: PR number to analyze
    """
    print(f"{Fore.GREEN}=== PR Impact Analysis Demo ==={Style.RESET_ALL}")
    print(f"{Fore.GREEN}=========================={Style.RESET_ALL}")

    # Step 1: Initialize Arc Memory
    print(f"\n{Fore.BLUE}Initializing Arc Memory...{Style.RESET_ALL}")
    arc = Arc(repo_path=repo_path)

    # Check if knowledge graph exists
    graph_exists = os.path.exists(os.path.expanduser("~/.arc/graph.db"))
    if not graph_exists:
        print(f"{Fore.RED}Error: Knowledge graph not found. Please run the Code Review Assistant demo first to build the graph.{Style.RESET_ALL}")
        sys.exit(1)
    else:
        print(f"{Fore.GREEN}Using existing knowledge graph...{Style.RESET_ALL}")

    # Step 2: Get PR details
    print(f"\n{Fore.BLUE}Fetching PR #{pr_number} details...{Style.RESET_ALL}")

    # Query the knowledge graph for PR details
    pr_entity_id = f"pr:{pr_number}"
    pr_details = None

    try:
        pr_details = arc.get_entity_details(pr_entity_id)
        print(f"{Fore.GREEN}Found PR: {pr_details.title}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error: Could not find PR #{pr_number}. Using simulated data instead.{Style.RESET_ALL}")
        # Simulate PR details for demo purposes
        pr_details = type('obj', (object,), {
            'id': pr_entity_id,
            'title': f"Simulated PR #{pr_number}",
            'body': "This is a simulated PR for demo purposes.",
            'properties': {
                'files_changed': [
                    'arc_memory/sdk/core.py',
                    'arc_memory/auto_refresh/core.py',
                    'docs/examples/agents/code_review_assistant.py'
                ]
            }
        })

    # Step 3: Get changed files
    print(f"\n{Fore.BLUE}Analyzing changed files...{Style.RESET_ALL}")

    # Get changed files from PR details or use simulated data
    changed_files = pr_details.properties.get('files_changed', []) if hasattr(pr_details, 'properties') else []

    # If no files found, use simulated data
    if not changed_files:
        changed_files = [
            'arc_memory/sdk/core.py',
            'arc_memory/auto_refresh/core.py',
            'docs/examples/agents/code_review_assistant.py'
        ]
        print(f"{Fore.YELLOW}No files found in PR. Using simulated data for demo.{Style.RESET_ALL}")

    print(f"{Fore.YELLOW}Files changed in PR #{pr_number}:{Style.RESET_ALL}")
    for file in changed_files:
        print(f"  - {file}")

    # Step 4: Analyze impact for each file
    print(f"\n{Fore.BLUE}Analyzing potential impact...{Style.RESET_ALL}")

    affected_components = set()
    total_impact_score = 0

    for file in changed_files:
        print(f"\n{Fore.YELLOW}Impact analysis for {file}:{Style.RESET_ALL}")

        # Get component impact
        component_id = f"file:{file}"
        impact_results = arc.analyze_component_impact(component_id=component_id)

        # Calculate impact score (0-1)
        impact_score = min(len(impact_results) / 10, 1.0)
        total_impact_score += impact_score

        # Display impact score
        impact_color = Fore.RED if impact_score > 0.7 else Fore.YELLOW if impact_score > 0.3 else Fore.GREEN
        print(f"  Impact Score: {impact_color}{impact_score:.2f}{Style.RESET_ALL}")

        # Display potentially affected components
        print(f"  Potentially Affected Components:")
        for result in impact_results[:5]:
            affected_components.add(result.title if hasattr(result, 'title') else str(result))
            print(f"    - {result.title if hasattr(result, 'title') else str(result)}")

    # Overall assessment
    avg_impact = total_impact_score / len(changed_files) if changed_files else 0
    risk_level = "High" if avg_impact > 0.7 else "Medium" if avg_impact > 0.3 else "Low"
    risk_color = Fore.RED if risk_level == "High" else Fore.YELLOW if risk_level == "Medium" else Fore.GREEN

    print(f"\n{Fore.YELLOW}📈 OVERALL ASSESSMENT{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}===================={Style.RESET_ALL}")
    print(f"Risk Level: {risk_color}{risk_level}{Style.RESET_ALL} ({avg_impact:.2f})")
    print(f"Affected Components: {len(affected_components)}")
    print(f"Review Priority: {risk_color}{'High' if risk_level == 'High' else 'Medium' if risk_level == 'Medium' else 'Low'}{Style.RESET_ALL}")

    # Recommendation
    print(f"\n{Fore.YELLOW}💡 RECOMMENDATION{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}================{Style.RESET_ALL}")
    if risk_level == "High":
        print("This PR has a high impact score and affects many components.")
        print("Recommend thorough review with domain experts for affected areas.")
    elif risk_level == "Medium":
        print("This PR has a moderate impact on the codebase.")
        print("Recommend standard review with attention to affected components.")
    else:
        print("This PR has minimal impact on the codebase.")
        print("Recommend standard review process.")

    print(f"\n{Fore.GREEN}=== Demo Complete ==={Style.RESET_ALL}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pr_impact_analysis.py <pr_number>")
        sys.exit(1)

    repo_path = "."  # Current directory
    pr_number = sys.argv[1]

    analyze_pr_impact(repo_path, pr_number)
