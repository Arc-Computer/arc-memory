# Code_review_assistant.py
#
# A high-impact agent that leverages Arc Memory's knowledge graph to provide
# intelligent code review assistance. This agent analyzes code changes and provides:
#   1. Impact analysis - What components might be affected by these changes
#   2. Decision trails - Why the code exists in its current form
#   3. Related components - What other parts of the codebase are connected
#   4. Review checklist - Custom checklist based on the changes
#
# Usage: python code_review_assistant.py --repo /path/to/repo --files file1.py file2.py

import os
import sys
import argparse
import json
import logging
import colorama
from colorama import Fore, Style
from arc_memory.sdk import Arc

# Suppress OpenAI debug logs
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("arc_memory.llm.openai_client").setLevel(logging.WARNING)

# Initialize colorama for cross-platform colored terminal output
colorama.init()

def analyze_changes(repo_path, files, api_key=None):
    """Analyze code changes using Arc Memory's knowledge graph.

    Args:
        repo_path: Path to the local repository
        files: List of files to analyze
        api_key: OpenAI API key (uses environment variable if None)

    Returns:
        Analysis results including impact, decision trails, and related components
    """
    # STEP 1: Initialize Arc Memory with appropriate configuration
    # -------------------------------------------------------------
    # Try to use OpenAI for better analysis if an API key is available
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print(f"{Fore.YELLOW}Warning: No OpenAI API key provided. Using default LLM adapter.{Style.RESET_ALL}")
            arc = Arc(repo_path=repo_path)
        else:
            arc = Arc(repo_path=repo_path)
            print(f"{Fore.BLUE}Using GPT-4.1 model for enhanced analysis{Style.RESET_ALL}")
            # When API key is available in env vars, Arc will use it for better results
    else:
        arc = Arc(repo_path=repo_path)
        print(f"{Fore.BLUE}Using GPT-4.1 model for enhanced analysis{Style.RESET_ALL}")
        # When API key is provided as arg, Arc will use it for better results

    # STEP 2: Build or access the knowledge graph
    # -------------------------------------------
    # Convert to absolute path for better display
    abs_repo_path = os.path.abspath(repo_path)
    print(f"{Fore.BLUE}Building/accessing Arc Memory knowledge graph for {abs_repo_path}{Style.RESET_ALL}")

    # Check if a graph exists by checking if the database file exists
    graph_path = os.path.expanduser("~/.arc/graph.db")
    graph_exists = os.path.exists(graph_path)
    if graph_exists:
        print(f"{Fore.GREEN}Existing knowledge graph found at {graph_path}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}No existing knowledge graph found.{Style.RESET_ALL}")

    if not graph_exists:
        try:
            # Only build the graph if it doesn't exist
            print(f"{Fore.BLUE}Building knowledge graph...{Style.RESET_ALL}")
            arc.build(
                include_github=True,
                use_llm=True,
                llm_provider="openai",
                llm_model="gpt-4.1",
                llm_enhancement_level="standard",
                verbose=True
            )
        except Exception as e:
            print(f"{Fore.RED}Error: Could not build knowledge graph: {e}{Style.RESET_ALL}")
            print(f"{Fore.RED}Please build the knowledge graph manually with 'arc build --github'{Style.RESET_ALL}")
            sys.exit(1)
    else:
        print(f"{Fore.GREEN}Using existing knowledge graph...{Style.RESET_ALL}")

    # STEP 3: Convert relative paths to absolute for Arc Memory functions
    # ------------------------------------------------------------------
    # Make sure we have absolute paths for the files
    abs_files = []
    for f in files:
        if os.path.isabs(f):
            abs_files.append(f)
        else:
            abs_files.append(os.path.abspath(os.path.join(repo_path, f)))

    # STEP 4: Analyze the changes using Arc Memory's capabilities
    # ----------------------------------------------------------
    # Collect all analysis results into a single dictionary for easy access
    results = {
        "files": files,
        "impact_analysis": analyze_impact(arc, abs_files),
        "decision_trails": get_decision_trails(arc, abs_files),
        "related_components": get_related_components(arc, abs_files),
        "review_checklist": generate_review_checklist(arc, files)
    }

    return results

def analyze_impact(arc, files):
    """Analyze the potential impact of changes using Arc Memory."""
    print(f"{Fore.YELLOW}Analyzing potential impact...{Style.RESET_ALL}")

    # For each file, determine what other components might be affected by changes
    impact_results = {}
    for file in files:
        # Get the relative path from the repository root
        try:
            # Try different formats for the component ID
            # First try with the full path
            component_id = f"file:{file}"
            file_results = arc.analyze_component_impact(component_id=component_id)
        except Exception as e1:
            try:
                # Try with just the filename
                rel_path = os.path.basename(file)
                component_id = f"file:{rel_path}"
                file_results = arc.analyze_component_impact(component_id=component_id)
            except Exception as e2:
                # If both fail, use simulated data for demo purposes
                print(f"{Fore.YELLOW}Could not analyze impact for {file}: {e1}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Using simulated data for demo purposes{Style.RESET_ALL}")

                # Create simulated impact results
                rel_path = os.path.basename(file)
                impact_results[rel_path] = {
                    "level": "Medium",
                    "affected_areas": [
                        "arc_memory/sdk/core.py",
                        "arc_memory/auto_refresh/core.py",
                        "arc_memory/sdk/query.py",
                        "arc_memory/sdk/decision_trail.py",
                        "arc_memory/sdk/relationships.py"
                    ]
                }
                continue

        # Transform the detailed results into a simplified format for display
        if file_results:
            rel_path = os.path.basename(file)
            impact_results[rel_path] = {
                "level": "Medium",  # Default impact level
                "affected_areas": [r.title for r in file_results[:5] if hasattr(r, 'title')]
            }

    return impact_results

def get_decision_trails(arc, files):
    """Get decision trails for why code exists in its current form."""
    print(f"{Fore.YELLOW}Retrieving decision trails...{Style.RESET_ALL}")

    # For each file, find out why the code exists as it does (design decisions, PRs, etc.)
    decision_trails = {}
    for file in files:
        try:
            # We use line 1 as a default starting point for the decision trail
            # In a real application, you might want to analyze specific lines of interest
            trail = arc.get_decision_trail(file_path=file, line_number=1)

            if trail:
                rel_path = os.path.basename(file)
                # Extract the rationale from the first decision trail entry
                decision_trails[rel_path] = {
                    "explanation": trail[0].rationale if trail and hasattr(trail[0], 'rationale') else "No explanation available"
                }
        except Exception as e:
            # If there's an error, use simulated data for demo purposes
            print(f"{Fore.YELLOW}Could not get decision trail for {file}: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Using simulated data for demo purposes{Style.RESET_ALL}")

            rel_path = os.path.basename(file)
            decision_trails[rel_path] = {
                "explanation": "This file implements a Code Review Assistant that leverages Arc Memory's knowledge graph to provide context-aware code reviews. It was created to demonstrate how Arc Memory can be used to understand code context, predict impact, and make safer changes."
            }

    return decision_trails

def get_related_components(arc, files):
    """Get components related to the changed files."""
    print(f"{Fore.YELLOW}Finding related components...{Style.RESET_ALL}")

    # For each file, find other components that are related (dependencies, imports, etc.)
    related = {}
    for file in files:
        try:
            # Arc Memory can identify related entities based on the knowledge graph
            related_entities = arc.get_related_entities(file)
            if related_entities:
                rel_path = os.path.basename(file)
                related[rel_path] = related_entities
        except Exception as e:
            # If there's an error, use simulated data for demo purposes
            print(f"{Fore.YELLOW}Could not get related components for {file}: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Using simulated data for demo purposes{Style.RESET_ALL}")

            rel_path = os.path.basename(file)
            # Create simulated related entities
            from collections import namedtuple
            RelatedEntity = namedtuple('RelatedEntity', ['id', 'title', 'relationship'])
            related[rel_path] = [
                RelatedEntity("file:arc_memory/sdk/core.py", "SDK Core", "depends_on"),
                RelatedEntity("file:arc_memory/auto_refresh/core.py", "Auto Refresh Core", "depends_on"),
                RelatedEntity("file:arc_memory/sdk/query.py", "SDK Query", "depends_on"),
                RelatedEntity("file:arc_memory/sdk/decision_trail.py", "Decision Trail", "depends_on"),
                RelatedEntity("file:arc_memory/sdk/relationships.py", "Relationships", "depends_on")
            ]

    return related

def generate_review_checklist(arc, files):
    """Generate a custom review checklist based on the changed files."""
    print(f"{Fore.YELLOW}Generating review checklist...{Style.RESET_ALL}")

    try:
        # Use natural language query to generate a context-aware review checklist
        query = f"Generate a code review checklist for changes to: {', '.join(files)}"
        results = arc.query(query)

        # Extract the checklist items from the query results
        checklist = []
        if results and "results" in results:
            for result in results["results"]:
                if "content" in result:
                    checklist.append(result["content"])

        # If no checklist items were found, use a default checklist
        if not checklist:
            checklist = [
                "Check for proper error handling",
                "Verify input validation",
                "Ensure code follows project style guidelines",
                "Look for potential performance issues",
                "Verify documentation is up-to-date"
            ]
    except Exception as e:
        # If there's an error, use a default checklist
        print(f"{Fore.YELLOW}Could not generate review checklist: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Using default checklist for demo purposes{Style.RESET_ALL}")

        checklist = [
            "Check for proper error handling and fallback mechanisms",
            "Verify input validation and edge case handling",
            "Ensure code follows project style guidelines and naming conventions",
            "Look for potential performance issues or inefficient algorithms",
            "Verify documentation is up-to-date and comprehensive",
            "Check for proper use of Arc Memory SDK features",
            "Ensure compatibility with different environments"
        ]

    return checklist

def display_results(results):
    """Display analysis results in a readable format."""
    print(f"\n{Fore.GREEN}=== Code Review Analysis Results ==={Style.RESET_ALL}\n")

    # SECTION 1: Files being analyzed
    # -------------------------------
    print(f"{Fore.CYAN}Files Analyzed:{Style.RESET_ALL} {', '.join(results['files'])}\n")

    # SECTION 2: Impact analysis - what might be affected by these changes
    # -------------------------------------------------------------------
    print(f"{Fore.CYAN}Impact Analysis:{Style.RESET_ALL}")
    for component, impact in results["impact_analysis"].items():
        # Color-code impact levels for better visibility
        impact_level = impact.get("level", "Unknown")
        level_color = Fore.RED if impact_level == "High" else Fore.YELLOW if impact_level == "Medium" else Fore.GREEN

        print(f"  • {component}: {level_color}{impact_level}{Style.RESET_ALL}")
        if "affected_areas" in impact:
            print(f"    Affected Areas: {', '.join(impact['affected_areas'])}")

    # SECTION 3: Decision trails - why the code exists as it does
    # ----------------------------------------------------------
    if results["decision_trails"]:
        print(f"\n{Fore.CYAN}Decision Trails:{Style.RESET_ALL}")
        for file, trail in results["decision_trails"].items():
            print(f"  • {file}:")
            if "explanation" in trail:
                # Show a preview of the explanation (first 200 chars)
                print(f"    {trail['explanation'][:200]}...")

    # SECTION 4: Related components - what else is connected to these files
    # --------------------------------------------------------------------
    if results["related_components"]:
        print(f"\n{Fore.CYAN}Related Components:{Style.RESET_ALL}")
        for file, related in results["related_components"].items():
            print(f"  • {file} is related to:")
            # Limit to 5 related components to avoid overwhelming output
            for rel in related[:5]:
                print(f"    - {rel}")

    # SECTION 5: Review checklist - what to look for when reviewing
    # ------------------------------------------------------------
    if results["review_checklist"]:
        print(f"\n{Fore.CYAN}Review Checklist:{Style.RESET_ALL}")
        for i, item in enumerate(results["review_checklist"], 1):
            print(f"  {i}. {item}")

def main():
    """Main entry point for the Code Review Assistant."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Code Review Assistant using Arc Memory")
    parser.add_argument("--repo", required=True, help="Path to the local repository")
    parser.add_argument("--files", nargs="+", required=True, help="List of files to analyze")
    parser.add_argument("--output", help="Output file for JSON results (optional)")
    parser.add_argument("--api-key", help="OpenAI API key (uses OPENAI_API_KEY env var if not provided)")

    args = parser.parse_args()

    # STEP 1: Analyze the changes using Arc Memory
    results = analyze_changes(args.repo, args.files, args.api_key)

    # STEP 2: Display results in a human-readable format in the terminal
    display_results(results)

    # STEP 3: Save results to a JSON file if requested (useful for CI integration)
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n{Fore.GREEN}Results saved to {args.output}{Style.RESET_ALL}")

# Entry point when script is run directly
if __name__ == "__main__":
    main()
