#!/usr/bin/env python3
"""
LLM-Powered Blast Radius Visualization

This script visualizes the potential impact (blast radius) of changes to a file
by creating a network graph of affected components. It leverages LLMs to provide
intelligent analysis of the impact and recommendations for mitigating risks.

Usage:
    python llm_powered_blast_radius.py <file_path>

Example:
    python llm_powered_blast_radius.py arc_memory/auto_refresh/core.py
"""

import os
import sys
import json
import argparse
import logging
import time
from pathlib import Path
import colorama
from colorama import Fore, Style

# Completely suppress all OpenAI and API-related debug logs
logging.getLogger("openai").setLevel(logging.CRITICAL)
logging.getLogger("arc_memory.llm").setLevel(logging.CRITICAL)
logging.getLogger("arc_memory.llm.openai_client").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger().setLevel(logging.WARNING)

# Monkey patch the OpenAI client's logger to completely suppress the "Acknowledged" messages
import arc_memory.llm.openai_client
original_warning = arc_memory.llm.openai_client.logger.warning

def silent_warning(msg, *args, **kwargs):
    if "OpenAI API returned unexpected response" not in str(msg):
        original_warning(msg, *args, **kwargs)

arc_memory.llm.openai_client.logger.warning = silent_warning

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

class ProgressTracker:
    """Simple progress tracker for long-running operations."""
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.update_interval = 0.5  # Update progress bar every 0.5 seconds

    def update(self, step_name: str = ""):
        self.current_step += 1
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self.last_update_time = current_time
            percent = int((self.current_step / self.total_steps) * 100)
            elapsed = current_time - self.start_time
            bar_length = 30
            filled_length = int(bar_length * self.current_step / self.total_steps)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)

            # Clear the current line and print the progress bar
            print(f"\r{Fore.BLUE}[{bar}] {percent}% | {elapsed:.1f}s | {step_name}{' ' * 20}{Style.RESET_ALL}", end='', flush=True)

    def complete(self):
        print(f"\r{Fore.GREEN}[{'█' * 30}] 100% | {time.time() - self.start_time:.1f}s | Complete{' ' * 20}{Style.RESET_ALL}")
        print()

def get_llm_impact_analysis(arc, file_path, impact_results):
    """
    Use LLM to analyze the impact of changes to a file.

    Args:
        arc: Arc Memory instance
        file_path: Path to the file being analyzed
        impact_results: Results from analyze_component_impact

    Returns:
        Dictionary with LLM analysis results
    """
    # Create a progress tracker
    progress = ProgressTracker(3)  # 3 steps: context gathering, LLM query, processing results

    # Step 1: Gather context about the file and its impact
    progress.update("Gathering context")

    # Format impact results for the LLM
    impact_context = []
    for result in impact_results:
        impact_info = {
            "component": result.title if hasattr(result, 'title') else "Unknown",
            "id": result.id if hasattr(result, 'id') else "Unknown",
            "impact_score": result.impact_score if hasattr(result, 'impact_score') else 0.5,
            "impact_type": result.impact_type if hasattr(result, 'impact_type') else "unknown"
        }
        impact_context.append(impact_info)

    # Get file content (first 1000 chars)
    file_content = ""
    try:
        with open(file_path, 'r') as f:
            file_content = f.read(1000)
    except Exception as e:
        file_content = f"Could not read file: {e}"

    # Step 2: Query the LLM for analysis
    progress.update("Analyzing impact with LLM")

    query = f"""
    I'm analyzing the potential impact (blast radius) of changes to the file {file_path}.

    Here's what I know about the file:
    ```
    {file_content}
    ```

    Here are the components that might be affected by changes to this file:
    {json.dumps(impact_context, indent=2)}

    Based on this information, please provide:

    1. An overall assessment of the blast radius (high/medium/low) and why
    2. Specific risks associated with changing this file
    3. Recommendations for safely making changes to this file
    4. Testing strategies to ensure changes don't break dependent components

    Be specific and reference actual components, functions, or patterns from the knowledge graph.
    Mention specific file names and relationships when possible.
    """

    try:
        # Use the query method which leverages LLMs to process natural language against the graph
        analysis_results = arc.query(query)

        # Step 3: Process the results
        progress.update("Processing results")

        # Extract the analysis
        analysis = {
            "assessment": analysis_results.answer if hasattr(analysis_results, "answer") else "",
            "reasoning": analysis_results.reasoning if hasattr(analysis_results, "reasoning") else "",
            "evidence": []
        }

        # Extract evidence
        if hasattr(analysis_results, "evidence"):
            for evidence in analysis_results.evidence[:3]:  # Limit to top 3 pieces of evidence
                if hasattr(evidence, "content"):
                    analysis["evidence"].append(evidence.content)

        progress.complete()
        return analysis

    except Exception as e:
        print(f"\n{Fore.YELLOW}Error getting LLM analysis: {e}{Style.RESET_ALL}")
        progress.complete()
        return {
            "assessment": f"Could not complete analysis: {e}",
            "reasoning": "",
            "evidence": []
        }

def find_key_files(arc):
    """
    Find key files in the repository that are guaranteed to have rich data in the knowledge graph.

    Args:
        arc: Arc Memory instance

    Returns:
        List of key files with their component IDs
    """
    # Try to find key files using a query
    try:
        query = "What are the most important files in the repository? List the top 5 files with their component IDs."
        print(f"{Fore.BLUE}Querying for key files in the repository...{Style.RESET_ALL}")
        query_result = arc.query(query)

        # Try to extract component IDs from the response
        if hasattr(query_result, "answer"):
            import re
            # Look for file: patterns in the answer
            matches = re.findall(r'file:[^\s,\'")\]]+', query_result.answer)
            if matches:
                key_files = []
                for match in matches[:5]:  # Limit to top 5
                    component_id = match
                    file_path = component_id.replace("file:", "")
                    key_files.append((file_path, component_id))
                return key_files
    except Exception as e:
        print(f"{Fore.YELLOW}Error querying for key files: {e}{Style.RESET_ALL}")

    # Fallback: Return a list of known important files
    return [
        ("arc_memory/sdk/core.py", "file:arc_memory/sdk/core.py"),
        ("arc_memory/auto_refresh/core.py", "file:arc_memory/auto_refresh/core.py"),
        ("arc_memory/sdk/query.py", "file:arc_memory/sdk/query.py"),
        ("arc_memory/sdk/impact.py", "file:arc_memory/sdk/impact.py"),
        ("arc_memory/sdk/decision_trail.py", "file:arc_memory/sdk/decision_trail.py")
    ]

def get_real_impact_data(arc, file_path):
    """
    Get real impact data for a file from the knowledge graph.

    Args:
        arc: Arc Memory instance
        file_path: Path to the file to analyze

    Returns:
        List of impact results, component ID used, and whether real data was found
    """
    # Try multiple approaches to find the component in the knowledge graph
    impact_results = []
    component_id_used = None

    # Approach 1: Try with the full path
    try:
        component_id = f"file:{file_path}"
        print(f"{Fore.BLUE}Trying component ID: {component_id}{Style.RESET_ALL}")
        impact_results = arc.analyze_component_impact(component_id=component_id, max_depth=3)
        if impact_results:
            print(f"{Fore.GREEN}Found component with ID: {component_id}{Style.RESET_ALL}")
            component_id_used = component_id
            return impact_results, component_id_used, True
    except Exception as e:
        print(f"{Fore.YELLOW}Error with full path: {e}{Style.RESET_ALL}")

    # Approach 2: Try with absolute path
    try:
        abs_path = os.path.abspath(file_path)
        component_id = f"file:{abs_path}"
        print(f"{Fore.BLUE}Trying component ID: {component_id}{Style.RESET_ALL}")
        impact_results = arc.analyze_component_impact(component_id=component_id, max_depth=3)
        if impact_results:
            print(f"{Fore.GREEN}Found component with ID: {component_id}{Style.RESET_ALL}")
            component_id_used = component_id
            return impact_results, component_id_used, True
    except Exception as e:
        print(f"{Fore.YELLOW}Error with absolute path: {e}{Style.RESET_ALL}")

    # Approach 3: Try with just the filename
    try:
        component_id = f"file:{os.path.basename(file_path)}"
        print(f"{Fore.BLUE}Trying component ID: {component_id}{Style.RESET_ALL}")
        impact_results = arc.analyze_component_impact(component_id=component_id, max_depth=3)
        if impact_results:
            print(f"{Fore.GREEN}Found component with ID: {component_id}{Style.RESET_ALL}")
            component_id_used = component_id
            return impact_results, component_id_used, True
    except Exception as e:
        print(f"{Fore.YELLOW}Error with filename: {e}{Style.RESET_ALL}")

    # No real data found
    return [], None, False

def visualize_blast_radius(repo_path, file_path):
    """
    Visualize the blast radius of changes to a file.

    Args:
        repo_path: Path to the repository
        file_path: Path to the file to analyze
    """
    print(f"{Fore.GREEN}=== LLM-Powered Blast Radius Visualization ==={Style.RESET_ALL}")
    print(f"{Fore.GREEN}=========================================={Style.RESET_ALL}")

    # Step 1: Initialize Arc Memory
    print(f"\n{Fore.BLUE}Initializing Arc Memory...{Style.RESET_ALL}")
    arc = Arc(repo_path=repo_path)

    # Check if knowledge graph exists
    graph_exists = os.path.exists(os.path.expanduser("~/.arc/graph.db"))
    if not graph_exists:
        print(f"{Fore.RED}Error: Knowledge graph not found. Please run 'arc build --github' to build the graph.{Style.RESET_ALL}")
        sys.exit(1)
    else:
        print(f"{Fore.GREEN}Using existing knowledge graph...{Style.RESET_ALL}")

    # Step 2: Analyze component impact
    print(f"\n{Fore.BLUE}Analyzing impact for {file_path}...{Style.RESET_ALL}")

    # Try to get real impact data for the specified file
    impact_results, component_id_used, real_data_found = get_real_impact_data(arc, file_path)

    # If no real data found, try key files until we find one with data
    if not real_data_found:
        print(f"{Fore.YELLOW}No impact data found for {file_path}. Trying key files...{Style.RESET_ALL}")
        key_files = find_key_files(arc)

        for key_file_path, key_component_id in key_files:
            print(f"{Fore.BLUE}Trying key file: {key_file_path}{Style.RESET_ALL}")
            try:
                key_impact_results = arc.analyze_component_impact(component_id=key_component_id, max_depth=3)
                if key_impact_results:
                    print(f"{Fore.GREEN}Found impact data for key file: {key_file_path}{Style.RESET_ALL}")
                    impact_results = key_impact_results
                    file_path = key_file_path  # Update file_path to the key file
                    component_id_used = key_component_id
                    real_data_found = True
                    break
            except Exception as e:
                print(f"{Fore.YELLOW}Error with key file {key_file_path}: {e}{Style.RESET_ALL}")

    # If still no real data found, use simulated data
    if not real_data_found:
        print(f"{Fore.YELLOW}No impact data found for any key files. Using simulated data for demo.{Style.RESET_ALL}")
        # Create simulated impact results for demo purposes
        from collections import namedtuple
        ImpactResult = namedtuple('ImpactResult', ['id', 'title', 'impact_score', 'impact_type'])
        impact_results = [
            ImpactResult(f"file:arc_memory/sdk/core.py", "SDK Core", 0.9, "direct"),
            ImpactResult(f"file:arc_memory/sdk/models.py", "SDK Models", 0.8, "direct"),
            ImpactResult(f"file:arc_memory/sdk/adapters/openai.py", "OpenAI Adapter", 0.7, "indirect"),
            ImpactResult(f"file:arc_memory/sdk/adapters/langchain.py", "LangChain Adapter", 0.6, "indirect"),
            ImpactResult(f"file:docs/examples/agents/llm_powered_code_review.py", "LLM-Powered Code Review", 0.5, "indirect"),
            ImpactResult(f"file:docs/examples/agents/incident_response_navigator.py", "Incident Response Navigator", 0.4, "indirect"),
            ImpactResult(f"file:arc_memory/cli/why.py", "Why Command", 0.3, "indirect"),
            ImpactResult(f"file:arc_memory/cli/relate.py", "Relate Command", 0.2, "indirect")
        ]

    print(f"{Fore.GREEN}Found {len(impact_results)} potentially affected components{Style.RESET_ALL}")

    # Step 3: Get LLM analysis of the impact
    print(f"\n{Fore.BLUE}Getting LLM analysis of impact...{Style.RESET_ALL}")
    llm_analysis = get_llm_impact_analysis(arc, file_path, impact_results)

    # Step 4: Create network graph
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

    # Step 5: Visualize the graph
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

    # Print LLM analysis
    print(f"\n{Fore.CYAN}LLM Analysis of Impact:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 20}{Style.RESET_ALL}")

    if llm_analysis["assessment"]:
        # Split the assessment into sections based on numbered points
        assessment_lines = llm_analysis["assessment"].split('\n')
        current_section = []
        sections = []

        for line in assessment_lines:
            if line.strip().startswith(('1.', '2.', '3.', '4.')):
                if current_section:
                    sections.append('\n'.join(current_section))
                    current_section = []
            current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section))

        # Display each section with appropriate formatting
        for section in sections:
            if section.strip().startswith('1.'):
                print(f"{Fore.YELLOW}Overall Assessment:{Style.RESET_ALL}")
            elif section.strip().startswith('2.'):
                print(f"{Fore.YELLOW}Specific Risks:{Style.RESET_ALL}")
            elif section.strip().startswith('3.'):
                print(f"{Fore.YELLOW}Recommendations:{Style.RESET_ALL}")
            elif section.strip().startswith('4.'):
                print(f"{Fore.YELLOW}Testing Strategies:{Style.RESET_ALL}")

            print(f"{section.strip()}\n")
    else:
        print(f"{Fore.RED}No LLM analysis available.{Style.RESET_ALL}")

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
    parser = argparse.ArgumentParser(description="LLM-Powered Blast Radius Visualization")
    parser.add_argument("file_path", help="Path to the file to analyze")
    parser.add_argument("--repo", default=".", help="Path to the repository (default: current directory)")

    args = parser.parse_args()

    visualize_blast_radius(args.repo, args.file_path)
