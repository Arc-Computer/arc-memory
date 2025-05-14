#!/usr/bin/env python3
"""
Blast Radius Visualization Demo

This script visualizes the potential impact (blast radius) of changes to a file
by creating a network graph of affected components.

Usage:
    python blast_radius_viz.py <file_path>

Example:
    python blast_radius_viz.py arc_memory/auto_refresh/core.py
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
    import matplotlib.pyplot as plt
    import networkx as nx
except ImportError:
    print(f"{Fore.RED}Error: Required packages not found. Please install them with:")
    print(f"pip install matplotlib networkx{Style.RESET_ALL}")
    sys.exit(1)

try:
    from arc_memory.sdk import Arc
except ImportError:
    print(f"{Fore.RED}Error: Arc Memory SDK not found. Please install it with 'pip install arc-memory'.{Style.RESET_ALL}")
    sys.exit(1)

def visualize_blast_radius(repo_path, file_path):
    """
    Visualize the blast radius of changes to a file.

    Args:
        repo_path: Path to the repository
        file_path: Path to the file to analyze
    """
    print(f"{Fore.GREEN}=== Blast Radius Visualization Demo ==={Style.RESET_ALL}")
    print(f"{Fore.GREEN}==================================={Style.RESET_ALL}")

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

    # Step 2: Analyze component impact
    print(f"\n{Fore.BLUE}Analyzing impact for {file_path}...{Style.RESET_ALL}")

    # Get component impact
    component_id = f"file:{file_path}"
    impact_results = arc.analyze_component_impact(component_id=component_id, max_depth=3)

    if not impact_results:
        print(f"{Fore.YELLOW}No impact results found. Using simulated data for demo.{Style.RESET_ALL}")
        # Create simulated impact results for demo purposes
        from collections import namedtuple
        ImpactResult = namedtuple('ImpactResult', ['id', 'title', 'impact_score', 'impact_type'])
        impact_results = [
            ImpactResult(f"file:arc_memory/sdk/core.py", "SDK Core", 0.9, "direct"),
            ImpactResult(f"file:arc_memory/sdk/models.py", "SDK Models", 0.8, "direct"),
            ImpactResult(f"file:arc_memory/sdk/adapters/openai.py", "OpenAI Adapter", 0.7, "indirect"),
            ImpactResult(f"file:arc_memory/sdk/adapters/langchain.py", "LangChain Adapter", 0.6, "indirect"),
            ImpactResult(f"file:docs/examples/agents/code_review_assistant.py", "Code Review Assistant", 0.5, "indirect"),
            ImpactResult(f"file:docs/examples/agents/incident_response_navigator.py", "Incident Response Navigator", 0.4, "indirect"),
            ImpactResult(f"file:arc_memory/cli/why.py", "Why Command", 0.3, "indirect"),
            ImpactResult(f"file:arc_memory/cli/relate.py", "Relate Command", 0.2, "indirect")
        ]

    print(f"{Fore.GREEN}Found {len(impact_results)} potentially affected components{Style.RESET_ALL}")

    # Step 3: Create network graph
    print(f"\n{Fore.BLUE}Creating network visualization...{Style.RESET_ALL}")

    # Create a directed graph
    G = nx.DiGraph()

    # Add the central node (the file being analyzed)
    central_node = os.path.basename(file_path)
    G.add_node(central_node, type="central")

    # Add nodes and edges for impact results
    for result in impact_results:
        # Extract the filename from the component ID
        if hasattr(result, 'id') and result.id.startswith("file:"):
            node_name = os.path.basename(result.id[5:])  # Remove "file:" prefix
        else:
            node_name = result.title if hasattr(result, 'title') else "Unknown"

        # Add node
        G.add_node(node_name, type=getattr(result, 'impact_type', "unknown"))

        # Add edge with weight based on impact score
        impact_score = getattr(result, 'impact_score', 0.5)
        G.add_edge(central_node, node_name, weight=impact_score)

    # Step 4: Visualize the graph
    plt.figure(figsize=(12, 8))

    # Define node colors based on type
    node_colors = []
    for node in G.nodes():
        if node == central_node:
            node_colors.append('red')  # Central node
        elif G.nodes[node]['type'] == "direct":
            node_colors.append('orange')  # Direct impact
        else:
            node_colors.append('blue')  # Indirect impact

    # Define node sizes based on importance
    node_sizes = []
    for node in G.nodes():
        if node == central_node:
            node_sizes.append(1000)  # Central node
        elif G.nodes[node]['type'] == "direct":
            node_sizes.append(700)  # Direct impact
        else:
            node_sizes.append(500)  # Indirect impact

    # Define edge weights based on impact score
    edge_weights = [G[u][v]['weight'] * 3 for u, v in G.edges()]

    # Use a spring layout for the graph
    pos = nx.spring_layout(G, seed=42)

    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8)
    nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.5, edge_color='gray', arrows=True, arrowsize=15)
    nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')

    # Set title and remove axis
    plt.title(f"Blast Radius Analysis for {file_path}", fontsize=16)
    plt.axis('off')

    # Save the figure
    output_file = "blast_radius.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\n{Fore.GREEN}Blast radius visualization saved to {output_file}{Style.RESET_ALL}")
    print(f"Identified {len(impact_results)} potentially affected components")

    # Print impact summary
    print(f"\n{Fore.YELLOW}Top 5 Most Affected Components:{Style.RESET_ALL}")
    for i, result in enumerate(sorted(impact_results[:5], key=lambda x: getattr(x, 'impact_score', 0), reverse=True)):
        title = result.title if hasattr(result, 'title') else f"Component {i}"
        impact_score = getattr(result, 'impact_score', 0.5)
        print(f"  {i+1}. {title} (Impact Score: {impact_score:.2f})")

    print(f"\n{Fore.BLUE}Opening visualization...{Style.RESET_ALL}")

    # Open the image (platform-specific)
    if sys.platform == 'darwin':  # macOS
        os.system(f"open {output_file}")
    elif sys.platform == 'win32':  # Windows
        os.system(f"start {output_file}")
    else:  # Linux
        os.system(f"xdg-open {output_file}")

    print(f"\n{Fore.GREEN}=== Demo Complete ==={Style.RESET_ALL}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python blast_radius_viz.py <file_path>")
        sys.exit(1)

    repo_path = "."  # Current directory
    file_path = sys.argv[1]

    visualize_blast_radius(repo_path, file_path)
