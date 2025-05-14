# simplified_incident_response_navigator.py
#
# A high-impact agent that leverages Arc Memory's knowledge graph to assist with
# incident response and debugging. This agent analyzes incidents and provides:
#   1. Component relationships - How affected components are connected
#   2. Temporal changes - What changed between working and failing states
#   3. Similar incidents - Historical patterns that match the current issue
#   4. Root cause predictions - Likely sources of the problem
#   5. Resolution recommendations - Suggested fixes based on the knowledge graph
#
# Usage: python simplified_incident_response_navigator.py --repo /path/to/repo --components component1.py component2.py

import os
import argparse
import json
import datetime
import colorama
from colorama import Fore, Style
from arc_memory.sdk import Arc

# Initialize colorama for cross-platform colored terminal output
colorama.init()

def analyze_incident(repo_path, components, error_message=None, last_working_commit=None, current_commit=None, api_key=None):
    """Analyze an incident using Arc Memory's knowledge graph.

    Args:
        repo_path: Path to the local repository
        components: List of affected components or files
        error_message: Error message or description of the incident
        last_working_commit: Last known working commit hash
        current_commit: Current (failing) commit hash
        api_key: OpenAI API key (uses environment variable if None)

    Returns:
        Analysis results including root causes, temporal changes, and recommendations
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
            print(f"{Fore.BLUE}Using OpenAI adapter with GPT-4.1 model for enhanced analysis{Style.RESET_ALL}")
            # When API key is available in env vars, Arc will use it for better results
    else:
        arc = Arc(repo_path=repo_path)
        print(f"{Fore.BLUE}Using OpenAI adapter with GPT-4.1 model for enhanced analysis{Style.RESET_ALL}")
        # When API key is provided as arg, Arc will use it for better results

    # STEP 2: Build or access the knowledge graph
    # -------------------------------------------
    print(f"{Fore.BLUE}Building/accessing Arc Memory knowledge graph for {repo_path}...{Style.RESET_ALL}")

    # Check if a graph exists and is up to date
    graph_exists = False
    try:
        # Try to execute a simple query to check if the graph exists
        test_query = arc.query("test", max_results=1)
        if test_query is not None:
            graph_exists = True
            print(f"{Fore.GREEN}Existing knowledge graph found.{Style.RESET_ALL}")
    except Exception:
        # If the query fails, the graph doesn't exist or is not accessible
        graph_exists = False
        print(f"{Fore.YELLOW}No existing knowledge graph found.{Style.RESET_ALL}")

    try:
        # Always use the build method, which will handle both initial builds and incremental updates
        # The build method now uses the refresh_knowledge_graph function which supports incremental updates
        print(f"{Fore.BLUE}{'Refreshing' if graph_exists else 'Building'} knowledge graph...{Style.RESET_ALL}")
        # Use "fast" enhancement level for refreshes to reduce latency
        arc.build(
            include_github=True,
            use_llm=True if api_key else False,
            llm_provider="openai" if api_key else "ollama",
            llm_model="gpt-4.1" if api_key else None,
            llm_enhancement_level="fast" if graph_exists else "standard",
            # Fast for refreshes, standard for new builds
            verbose=True
        )
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not build/refresh knowledge graph: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Continuing with existing knowledge graph if available...{Style.RESET_ALL}")

    # STEP 3: Convert relative paths to absolute for Arc Memory functions
    # ------------------------------------------------------------------
    abs_components = [os.path.join(repo_path, c) for c in components]

    # STEP 4: Analyze the incident using Arc Memory's capabilities
    # -----------------------------------------------------------
    # Collect all analysis results into a single dictionary for easy access
    results = {
        "affected_components": components,
        "component_relationships": map_component_relationships(arc, abs_components),
        "temporal_changes": analyze_temporal_changes(arc, abs_components, last_working_commit, current_commit),
        "similar_incidents": find_similar_incidents(arc, abs_components, error_message),
        "root_cause_predictions": predict_root_causes(arc, abs_components, error_message),
        "resolution_recommendations": recommend_resolutions(arc, abs_components, error_message)
    }

    # STEP 5: Generate a postmortem if we have all the necessary information
    # ---------------------------------------------------------------------
    # A postmortem requires error message and commit information to be meaningful
    if error_message and last_working_commit and current_commit:
        results["postmortem"] = generate_postmortem(
            arc, abs_components, error_message, last_working_commit, current_commit
        )

    return results

def map_component_relationships(arc, components):
    """Map relationships between affected components.

    Identifies how components are connected to each other in the codebase,
    which helps understand the scope and impact of the incident.
    """
    print(f"{Fore.YELLOW}Mapping component relationships...{Style.RESET_ALL}")

    # For each affected component, find related entities in the knowledge graph
    relationships = {}
    for component in components:
        # Arc Memory can identify dependencies, imports, and other relationships
        related = arc.get_related_entities(component)
        if related:
            # Store with just the filename as the key for cleaner output
            rel_path = os.path.basename(component)
            relationships[rel_path] = related

    return relationships

def analyze_temporal_changes(arc, components, last_working_commit, current_commit):
    """Analyze changes between working and failing states.

    This function identifies what changed between the last known working state
    and the current failing state, which is crucial for pinpointing the cause
    of the incident.
    """
    print(f"{Fore.YELLOW}Analyzing temporal changes...{Style.RESET_ALL}")

    # APPROACH 1: If we have specific commit hashes, compare those directly
    # --------------------------------------------------------------------
    if not last_working_commit or not current_commit:
        # Fall back to time-based analysis if commit hashes aren't available
        return analyze_recent_changes(arc, components)

    # APPROACH 2: Use natural language queries to analyze changes between commits
    # -------------------------------------------------------------------------
    # We use Arc's query capability to ask about specific changes between commits
    changes = []

    for component in components:
        # Formulate a natural language query about what changed
        query = f"What changed in {component} between commit {last_working_commit} and {current_commit}?"
        results = arc.query(query)

        # Process and structure the results
        if results and hasattr(results, 'results'):
            component_changes = {
                "file": os.path.basename(component),
                "type": "Modified",  # Default to Modified since we're comparing versions
                "details": results.results[0].content if results.results else "No details available"
            }
            changes.append(component_changes)

    return {"changes": changes}

def analyze_recent_changes(arc, components):
    """Analyze recent changes to the affected components.

    When specific commit information isn't available, we can still analyze
    recent changes to identify potential causes of the incident.
    """
    # For each component, query for changes in the recent past (last 2 weeks)
    recent_changes = {}

    for component in components:
        # Use a time-based query to find recent changes
        query = f"What changes were made to {component} in the last 2 weeks?"
        results = arc.query(query)

        # Process and store the results
        if results and "results" in results:
            rel_path = os.path.basename(component)
            recent_changes[rel_path] = results["results"]

    return {"recent_changes": recent_changes}

def find_similar_incidents(arc, components, error_message):
    """Find similar past incidents based on components and error message.

    Identifying similar past incidents helps leverage institutional knowledge
    and previous solutions, potentially saving significant debugging time.
    """
    print(f"{Fore.YELLOW}Finding similar incidents...{Style.RESET_ALL}")

    # Build a natural language query that includes both components and error message
    query_parts = []

    # Include the affected components in the query
    component_str = ", ".join([os.path.basename(c) for c in components])
    query_parts.append(f"components: {component_str}")

    # Include the error message if available
    if error_message:
        query_parts.append(f"error: {error_message}")

    # Combine the parts into a complete query
    query = f"Find similar incidents with {' and '.join(query_parts)}"
    results = arc.query(query)

    # Extract and return the similar incidents from the query results
    similar_incidents = []
    if results and "results" in results:
        similar_incidents = results["results"]

    return similar_incidents

def predict_root_causes(arc, components, error_message):
    """Predict potential root causes based on the knowledge graph.

    Using the knowledge graph to predict root causes can significantly
    accelerate the debugging process by focusing attention on the most
    likely sources of the problem.
    """
    print(f"{Fore.YELLOW}Predicting root causes...{Style.RESET_ALL}")

    # Build a query that leverages Arc's knowledge graph to predict root causes
    query_parts = []

    # Include the affected components in the query
    component_str = ", ".join([os.path.basename(c) for c in components])
    query_parts.append(f"components: {component_str}")

    # Include the error message if available for more accurate predictions
    if error_message:
        query_parts.append(f"error: {error_message}")

    # Combine the parts into a complete query
    query = f"Predict root causes for incident with {' and '.join(query_parts)}"
    results = arc.query(query)

    # Extract and return the predicted root causes
    root_causes = []
    if results and "results" in results:
        root_causes = results["results"]

    return root_causes

def recommend_resolutions(arc, components, error_message):
    """Recommend potential resolutions based on the knowledge graph.

    After identifying root causes, this function suggests potential fixes
    based on the knowledge graph, which may include solutions from similar
    past incidents or best practices for the affected components.
    """
    print(f"{Fore.YELLOW}Recommending resolutions...{Style.RESET_ALL}")

    # Build a query to get resolution recommendations from Arc Memory
    query_parts = []

    # Include the affected components in the query
    component_str = ", ".join([os.path.basename(c) for c in components])
    query_parts.append(f"components: {component_str}")

    # Include the error message if available for more targeted recommendations
    if error_message:
        query_parts.append(f"error: {error_message}")

    # Combine the parts into a complete query
    query = f"Recommend resolutions for incident with {' and '.join(query_parts)}"
    results = arc.query(query)

    # Extract and return the recommended resolutions
    recommendations = []
    if results and "results" in results:
        recommendations = results["results"]

    return recommendations

def generate_postmortem(arc, components, error_message, last_working_commit, current_commit):
    """Generate a detailed postmortem with causal analysis.

    A postmortem documents what happened, why it happened, and how to prevent
    similar incidents in the future. This is valuable both for resolving the
    current incident and for building institutional knowledge.
    """
    print(f"{Fore.YELLOW}Generating postmortem...{Style.RESET_ALL}")

    # Create a comprehensive query that includes all relevant information
    query = (
        f"Generate a postmortem for an incident with error: {error_message}, "
        f"affecting components: {', '.join([os.path.basename(c) for c in components])}, "
        f"between commits {last_working_commit} and {current_commit}"
    )
    results = arc.query(query)

    # Structure the postmortem with a summary and detailed information
    postmortem = {
        # Extract the summary from the query results
        "summary": results["results"][0]["content"] if results and "results" in results else "",

        # Include detailed information about the incident
        "incident_details": {
            "error_message": error_message,
            "affected_components": [os.path.basename(c) for c in components],
            "last_working_commit": last_working_commit,
            "current_commit": current_commit,
            "timestamp": datetime.datetime.now().isoformat()  # Record when the analysis was done
        }
    }

    return postmortem

def display_results(results):
    """Display analysis results in a readable format.

    This function presents the analysis results in a structured, color-coded
    format that makes it easy to understand the incident and potential solutions.
    """
    print(f"\n{Fore.GREEN}=== Incident Analysis Results ==={Style.RESET_ALL}\n")

    # SECTION 1: Affected components - what parts of the codebase are involved
    # -----------------------------------------------------------------------
    print(f"{Fore.CYAN}Affected Components:{Style.RESET_ALL} {', '.join(results['affected_components'])}\n")

    # SECTION 2: Root cause predictions - likely sources of the problem
    # ----------------------------------------------------------------
    if results["root_cause_predictions"]:
        print(f"{Fore.CYAN}Potential Root Causes:{Style.RESET_ALL}")
        for i, cause in enumerate(results["root_cause_predictions"], 1):
            print(f"  {i}. {cause.get('content', '')}")
        print()

    # SECTION 3: Component relationships - how components are connected
    # ----------------------------------------------------------------
    if results["component_relationships"]:
        print(f"{Fore.CYAN}Component Relationships:{Style.RESET_ALL}")
        for component, related in results["component_relationships"].items():
            print(f"  • {component} is related to:")
            # Limit to 5 related components to avoid overwhelming output
            for rel in related[:5]:
                print(f"    - {rel}")
        print()

    # SECTION 4: Temporal changes - what changed between working and failing states
    # ---------------------------------------------------------------------------
    if results["temporal_changes"]:
        print(f"{Fore.CYAN}Changes Between Working and Failing States:{Style.RESET_ALL}")

        if "recent_changes" in results["temporal_changes"]:
            # Display recent changes if no commit hashes were provided
            for component, changes in results["temporal_changes"]["recent_changes"].items():
                print(f"  • {component}:")
                # Show only first 3 changes for brevity
                for change in changes[:3]:
                    print(f"    - {change.get('content', '')}")
        else:
            # Display specific changes between commits
            for change in results["temporal_changes"].get("changes", [])[:5]:
                # Color-code change types for better visibility
                change_type = change.get("type", "Modified")
                type_color = Fore.GREEN if change_type == "Added" else Fore.RED if change_type == "Removed" else Fore.YELLOW

                print(f"  • {change.get('file', '')}: {type_color}{change_type}{Style.RESET_ALL}")
                print(f"    {change.get('details', '')}")
        print()

    # SECTION 5: Resolution recommendations - suggested fixes
    # ------------------------------------------------------
    if results["resolution_recommendations"]:
        print(f"{Fore.CYAN}Recommended Resolutions:{Style.RESET_ALL}")
        for i, resolution in enumerate(results["resolution_recommendations"], 1):
            print(f"  {i}. {resolution.get('content', '')}")
        print()

    # SECTION 6: Similar incidents - historical patterns that match
    # ------------------------------------------------------------
    if results["similar_incidents"]:
        print(f"{Fore.CYAN}Similar Past Incidents:{Style.RESET_ALL}")
        # Show only first 3 similar incidents for brevity
        for i, incident in enumerate(results["similar_incidents"][:3], 1):
            print(f"  {i}. {incident.get('description', '')}")
            print(f"     Resolution: {incident.get('resolution', '')}")
        print()

    # SECTION 7: Postmortem - comprehensive analysis of the incident
    # -------------------------------------------------------------
    if "postmortem" in results:
        print(f"{Fore.CYAN}Incident Postmortem Summary:{Style.RESET_ALL}")
        print(f"  {results['postmortem'].get('summary', 'No summary available')}")

def main():
    """Main entry point for the Incident Response Navigator."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Incident Response Navigator using Arc Memory")
    parser.add_argument("--repo", required=True, help="Path to the local repository")
    parser.add_argument("--components", nargs="+", required=True, help="Affected components or files")
    parser.add_argument("--error", help="Error message or description of the incident")
    parser.add_argument("--last-working", help="Last known working commit hash")
    parser.add_argument("--current", help="Current (failing) commit hash")
    parser.add_argument("--output", help="Output file for JSON results (optional)")
    parser.add_argument("--api-key", help="OpenAI API key (uses OPENAI_API_KEY env var if not provided)")

    args = parser.parse_args()

    # STEP 1: Analyze the incident using Arc Memory
    results = analyze_incident(
        args.repo,
        args.components,
        args.error,
        args.last_working,
        args.current,
        args.api_key
    )

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
