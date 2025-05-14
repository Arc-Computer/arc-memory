#!/usr/bin/env python3
"""
LLM-Powered Code Review Assistant

A high-impact agent that leverages Arc Memory's knowledge graph and LLMs to provide
intelligent code review assistance. This agent analyzes code changes and provides:
  1. Contextual understanding - What the code does and why it exists
  2. Impact analysis - What components might be affected by these changes
  3. Historical insights - How the code has evolved and why decisions were made
  4. Review recommendations - Specific suggestions based on codebase patterns

Usage: python llm_powered_code_review.py --repo /path/to/repo --files file1.py file2.py
"""

import os
import sys
import argparse
import json
import logging
import colorama
from colorama import Fore, Style
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

from arc_memory.sdk import Arc

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

def initialize_arc(repo_path: str, api_key: Optional[str] = None) -> Arc:
    """Initialize Arc Memory with appropriate configuration.

    Args:
        repo_path: Path to the local repository
        api_key: OpenAI API key (uses environment variable if None)

    Returns:
        Initialized Arc instance
    """
    # Try to use OpenAI for better analysis if an API key is available
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print(f"{Fore.YELLOW}Warning: No OpenAI API key provided. Using default LLM adapter.{Style.RESET_ALL}")
            arc = Arc(repo_path=repo_path)
        else:
            arc = Arc(repo_path=repo_path)
            print(f"{Fore.BLUE}Using GPT-4.1 model for enhanced analysis{Style.RESET_ALL}")
    else:
        arc = Arc(repo_path=repo_path)
        print(f"{Fore.BLUE}Using GPT-4.1 model for enhanced analysis{Style.RESET_ALL}")

    # Check if a graph exists
    graph_path = os.path.expanduser("~/.arc/graph.db")
    graph_exists = os.path.exists(graph_path)
    if graph_exists:
        print(f"{Fore.GREEN}Existing knowledge graph found at {graph_path}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}No existing knowledge graph found.{Style.RESET_ALL}")
        try:
            # Only build the graph if it doesn't exist
            print(f"{Fore.BLUE}Building knowledge graph...{Style.RESET_ALL}")
            arc.build(
                include_github=True,
                use_llm=True,
                llm_provider="openai",
                llm_model="gpt-4.1",
                llm_enhancement_level="fast",
                verbose=True
            )
        except Exception as e:
            print(f"{Fore.RED}Error: Could not build knowledge graph: {e}{Style.RESET_ALL}")
            print(f"{Fore.RED}Please build the knowledge graph manually with 'arc build --github'{Style.RESET_ALL}")
            sys.exit(1)

    return arc

def get_file_content(file_path: str) -> str:
    """Get the content of a file.

    Args:
        file_path: Path to the file

    Returns:
        Content of the file as a string
    """
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"{Fore.YELLOW}Could not read file {file_path}: {e}{Style.RESET_ALL}")
        return ""

def perform_llm_powered_review(arc: Arc, repo_path: str, files: List[str]) -> Dict[str, Any]:
    """Perform an LLM-powered code review using Arc Memory's knowledge graph.

    This function uses the LLM to actively query the knowledge graph and generate
    insights about the code being reviewed.

    Args:
        arc: Initialized Arc instance
        repo_path: Path to the local repository
        files: List of files to analyze

    Returns:
        Review results as a dictionary
    """
    print(f"{Fore.BLUE}Performing LLM-powered code review...{Style.RESET_ALL}")

    # Create a simple progress tracker
    class ProgressTracker:
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

    # Convert relative paths to absolute
    abs_files = []
    for f in files:
        if os.path.isabs(f):
            abs_files.append(f)
        else:
            abs_files.append(os.path.abspath(os.path.join(repo_path, f)))

    # Get file contents for context
    file_contents = {}
    for file_path in abs_files:
        content = get_file_content(file_path)
        if content:
            file_contents[file_path] = content

    # Initialize results dictionary
    results = {
        "files": files,
        "file_reviews": {},
        "overall_assessment": {},
    }

    # Calculate total steps for progress tracking
    # For each file: context gathering + LLM query + processing results
    # Plus overall assessment at the end
    total_steps = len(abs_files) * 3 + 1
    progress = ProgressTracker(total_steps)

    # Review each file individually
    for file_path in abs_files:
        file_name = os.path.basename(file_path)
        print(f"{Fore.YELLOW}Reviewing {file_name}...{Style.RESET_ALL}")

        # Skip if we couldn't read the file
        if file_path not in file_contents:
            print(f"{Fore.YELLOW}Skipping {file_name} (could not read file){Style.RESET_ALL}")
            continue

        # Get file content
        content = file_contents[file_path]

        # First, get some context about the file from the knowledge graph
        progress.update("Getting file history and context")

        # Get decision trail for the file (line 1 as a starting point)
        try:
            decision_trail = arc.get_decision_trail(file_path=file_path, line_number=1)
            decision_context = ""
            if decision_trail:
                decision_context = "File history:\n"
                for entry in decision_trail[:3]:  # Limit to first 3 entries
                    if hasattr(entry, 'rationale') and entry.rationale:
                        # Add commit ID if available
                        commit_id = entry.id.split(':')[-1][:8] if hasattr(entry, 'id') and ':' in entry.id else "unknown"
                        # Add timestamp if available
                        timestamp = entry.timestamp if hasattr(entry, 'timestamp') else ""
                        timestamp_str = f" ({timestamp})" if timestamp else ""

                        decision_context += f"- [commit:{commit_id}{timestamp_str}] {entry.rationale}\n"

                        # Add PR or issue reference if available
                        if hasattr(entry, 'related_entities'):
                            for related in entry.related_entities[:2]:  # Limit to first 2 related entities
                                if hasattr(related, 'id') and hasattr(related, 'title'):
                                    if 'pr:' in related.id or 'issue:' in related.id:
                                        entity_type = 'PR' if 'pr:' in related.id else 'Issue'
                                        entity_id = related.id.split(':')[-1]
                                        decision_context += f"  - Related {entity_type} #{entity_id}: {related.title}\n"
        except Exception as e:
            decision_context = f"Could not get decision trail: {e}\n"

        # Get related components
        try:
            component_id = f"file:{file_path}"
            related_entities = []
            try:
                related_entities = arc.get_related_entities(component_id)
            except:
                # Try with just the filename
                try:
                    component_id = f"file:{file_name}"
                    related_entities = arc.get_related_entities(component_id)
                except:
                    pass

            related_context = ""
            if related_entities:
                related_context = "Related components:\n"
                for entity in related_entities[:5]:  # Limit to first 5 entities
                    if hasattr(entity, 'title') and entity.title:
                        # Get entity type and ID
                        entity_type = "unknown"
                        entity_id = "unknown"
                        if hasattr(entity, 'id') and ':' in entity.id:
                            parts = entity.id.split(':')
                            entity_type = parts[0]
                            entity_id = parts[1]

                        # Get relationship type with more descriptive text
                        relationship = entity.relationship if hasattr(entity, 'relationship') else 'related'
                        rel_description = relationship
                        if relationship == "imports":
                            rel_description = "imports/uses"
                        elif relationship == "imported_by":
                            rel_description = "imported/used by"
                        elif relationship == "depends_on":
                            rel_description = "depends on"
                        elif relationship == "depended_by":
                            rel_description = "depended on by"

                        related_context += f"- {entity.title} ({rel_description})\n"
                        related_context += f"  Type: {entity_type}, ID: {entity_id}\n"

                        # Add additional properties if available
                        if hasattr(entity, 'properties'):
                            props = entity.properties
                            if isinstance(props, dict):
                                for key, value in props.items():
                                    if key in ['author', 'created_at', 'language', 'function_name', 'class_name']:
                                        related_context += f"  {key}: {value}\n"
        except Exception as e:
            related_context = f"Could not get related components: {e}\n"

        # Get impact analysis
        try:
            component_id = f"file:{file_path}"
            impact_results = []
            try:
                impact_results = arc.analyze_component_impact(component_id=component_id)
            except:
                # Try with just the filename
                try:
                    component_id = f"file:{file_name}"
                    impact_results = arc.analyze_component_impact(component_id=component_id)
                except:
                    pass

            impact_context = ""
            if impact_results:
                impact_context = "Impact analysis:\n"
                for result in impact_results[:5]:  # Limit to first 5 results
                    if hasattr(result, 'title') and result.title:
                        # Get impact score with descriptive text
                        impact_score = result.impact_score if hasattr(result, 'impact_score') else 0.0
                        impact_level = "unknown"
                        if impact_score > 0.8:
                            impact_level = "high"
                        elif impact_score > 0.5:
                            impact_level = "medium"
                        else:
                            impact_level = "low"

                        # Get impact type with descriptive text
                        impact_type = result.impact_type if hasattr(result, 'impact_type') else "unknown"
                        type_description = impact_type
                        if impact_type == "direct":
                            type_description = "direct dependency"
                        elif impact_type == "indirect":
                            type_description = "indirect dependency"
                        elif impact_type == "potential":
                            type_description = "potential impact (co-change pattern)"

                        impact_context += f"- {result.title} (impact: {impact_level}, type: {type_description})\n"

                        # Add impact path if available
                        if hasattr(result, 'impact_path') and result.impact_path:
                            path_str = " -> ".join([p.split(":")[-1] if ":" in p else p for p in result.impact_path])
                            impact_context += f"  Path: {path_str}\n"

                        # Add related entities if available
                        if hasattr(result, 'related_entities') and result.related_entities:
                            for entity in result.related_entities[:2]:  # Limit to first 2 related entities
                                if hasattr(entity, 'title'):
                                    impact_context += f"  Related: {entity.title}\n"
        except Exception as e:
            impact_context = f"Could not get impact analysis: {e}\n"

        # Combine all context
        graph_context = decision_context + related_context + impact_context

        # Use the LLM to query the knowledge graph about this file
        # This is where the magic happens - the LLM actively uses the graph to understand the code
        query = f"""
        I'm reviewing the file {file_name}. Here's what I know about it from the knowledge graph:

        {graph_context}

        Based on this context and the file content below, please help me understand:

        1. What is the purpose of this file and how does it fit into the codebase?
        2. What are the key components or functions in this file?
        3. What other parts of the codebase depend on or are affected by this file?
        4. Are there any historical decisions or design patterns I should be aware of?
        5. What should I focus on when reviewing changes to this file?

        Here's the content of the file:
        ```
        {content[:2000]}  # Limit to first 2000 chars to avoid token limits
        ```

        Provide a concise, specific analysis that combines insights from both the knowledge graph and the code itself.
        """

        try:
            # Use the query method which leverages LLMs to process natural language against the graph
            progress.update("Querying LLM for code insights")
            review_results = arc.query(query)

            # Extract the review insights
            progress.update("Processing review results")
            file_review = {
                "understanding": review_results.query_understanding if hasattr(review_results, "query_understanding") else "",
                "answer": review_results.answer if hasattr(review_results, "answer") else "",
                "reasoning": review_results.reasoning if hasattr(review_results, "reasoning") else "",
                "evidence": []
            }

            # Extract evidence from the results
            if hasattr(review_results, "evidence"):
                for evidence in review_results.evidence[:5]:  # Limit to top 5 pieces of evidence
                    if hasattr(evidence, "content"):
                        file_review["evidence"].append(evidence.content)

            # Add to results
            results["file_reviews"][file_name] = file_review

        except Exception as e:
            print(f"\n{Fore.YELLOW}Error reviewing {file_name}: {e}{Style.RESET_ALL}")
            # Add a placeholder review
            results["file_reviews"][file_name] = {
                "understanding": f"Error reviewing {file_name}",
                "answer": f"Could not complete review: {e}",
                "reasoning": "",
                "evidence": []
            }
            # Update progress for the remaining steps
            progress.update("Error occurred")
            progress.update("Skipping remaining steps")

    # Generate an overall assessment
    try:
        # First, gather context about all files from the knowledge graph
        progress.update("Generating overall assessment")

        # Get file summaries
        file_summaries = []
        for file_path in abs_files:
            file_name = os.path.basename(file_path)
            if file_name in results["file_reviews"]:
                review = results["file_reviews"][file_name]
                if "answer" in review and review["answer"]:
                    summary = review["answer"].split("\n")[0]  # Get first line as summary
                    file_summaries.append(f"{file_name}: {summary}")

        file_context = "\n".join(file_summaries)

        # Use the LLM to generate an overall assessment based on all files
        overall_query = f"""
        I'm reviewing changes to the following files:
        {', '.join(files)}

        Here's what I know about these files:
        {file_context}

        Based on this context and your knowledge of the codebase, please provide:

        1. An overall assessment of the impact of these changes
        2. Potential risks or areas of concern
        3. Recommendations for testing and validation
        4. Any architectural implications

        Focus on being specific and actionable. Provide concrete recommendations rather than general advice.
        Be sure to include specific file names, function names, and concrete examples from the knowledge graph.
        Mention specific commits, PRs, or issues that are relevant to these changes when possible.
        """

        overall_results = arc.query(overall_query)

        results["overall_assessment"] = {
            "summary": overall_results.answer if hasattr(overall_results, "answer") else "",
            "reasoning": overall_results.reasoning if hasattr(overall_results, "reasoning") else "",
        }

        # Complete the progress tracking
        progress.complete()

    except Exception as e:
        print(f"\n{Fore.YELLOW}Error generating overall assessment: {e}{Style.RESET_ALL}")
        results["overall_assessment"] = {
            "summary": "Could not generate overall assessment",
            "reasoning": f"Error: {e}"
        }
        # Complete the progress tracking even if there was an error
        progress.complete()

    return results

def display_review_results(results: Dict[str, Any]) -> None:
    """Display the review results in a readable format.

    Args:
        results: Review results dictionary
    """
    print(f"\n{Fore.GREEN}=== LLM-Powered Code Review Results ==={Style.RESET_ALL}\n")

    # Display files being analyzed
    print(f"{Fore.CYAN}Files Analyzed:{Style.RESET_ALL} {', '.join(results['files'])}\n")

    # Display individual file reviews
    for file_name, review in results["file_reviews"].items():
        print(f"{Fore.CYAN}Review for {file_name}:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * (len(file_name) + 11)}{Style.RESET_ALL}")

        # Display the main answer/insights
        if review["answer"]:
            # Split the answer into sections based on numbered points
            answer_lines = review["answer"].split('\n')
            current_section = []
            sections = []

            for line in answer_lines:
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
                    if current_section:
                        sections.append('\n'.join(current_section))
                        current_section = []
                current_section.append(line)

            if current_section:
                sections.append('\n'.join(current_section))

            # Display each section with appropriate formatting
            for section in sections:
                if section.strip().startswith('1.'):
                    print(f"{Fore.YELLOW}Purpose and Context:{Style.RESET_ALL}")
                elif section.strip().startswith('2.'):
                    print(f"{Fore.YELLOW}Key Components:{Style.RESET_ALL}")
                elif section.strip().startswith('3.'):
                    print(f"{Fore.YELLOW}Dependencies and Impact:{Style.RESET_ALL}")
                elif section.strip().startswith('4.'):
                    print(f"{Fore.YELLOW}Historical Context:{Style.RESET_ALL}")
                elif section.strip().startswith('5.'):
                    print(f"{Fore.YELLOW}Review Focus Areas:{Style.RESET_ALL}")

                print(f"{section.strip()}\n")

        # Display supporting evidence
        if review["evidence"]:
            print(f"{Fore.YELLOW}Supporting Evidence from Knowledge Graph:{Style.RESET_ALL}")
            for i, evidence in enumerate(review["evidence"], 1):
                print(f"  {i}. {evidence[:200]}..." if len(evidence) > 200 else f"  {i}. {evidence}")
            print()

    # Display overall assessment
    if "overall_assessment" in results and results["overall_assessment"]:
        print(f"{Fore.CYAN}Overall Assessment:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 18}{Style.RESET_ALL}")

        if results["overall_assessment"]["summary"]:
            # Split the summary into sections based on numbered points
            summary_lines = results["overall_assessment"]["summary"].split('\n')
            current_section = []
            sections = []

            for line in summary_lines:
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
                    print(f"{Fore.YELLOW}Impact Assessment:{Style.RESET_ALL}")
                elif section.strip().startswith('2.'):
                    print(f"{Fore.YELLOW}Potential Risks:{Style.RESET_ALL}")
                elif section.strip().startswith('3.'):
                    print(f"{Fore.YELLOW}Testing Recommendations:{Style.RESET_ALL}")
                elif section.strip().startswith('4.'):
                    print(f"{Fore.YELLOW}Architectural Implications:{Style.RESET_ALL}")

                print(f"{section.strip()}\n")
        else:
            print(f"\n{results['overall_assessment']['summary']}\n")

def main():
    """Main entry point for the LLM-Powered Code Review Assistant."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LLM-Powered Code Review Assistant using Arc Memory")
    parser.add_argument("--repo", required=True, help="Path to the local repository")
    parser.add_argument("--files", nargs="+", required=True, help="List of files to analyze")
    parser.add_argument("--output", help="Output file for JSON results (optional)")
    parser.add_argument("--api-key", help="OpenAI API key (uses OPENAI_API_KEY env var if not provided)")

    args = parser.parse_args()

    # Initialize Arc Memory
    arc = initialize_arc(args.repo, args.api_key)

    # Perform the LLM-powered code review
    start_time = time.time()
    results = perform_llm_powered_review(arc, args.repo, args.files)
    end_time = time.time()

    # Display results
    display_review_results(results)

    # Print execution time
    print(f"\n{Fore.BLUE}Review completed in {end_time - start_time:.2f} seconds{Style.RESET_ALL}")

    # Save results to a JSON file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n{Fore.GREEN}Results saved to {args.output}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
