#!/usr/bin/env python3
"""
Code Generation Agent

A specialized agent that generates improved code based on insights from code review
and blast radius analysis. This agent leverages Arc Memory's knowledge graph to:
  1. Understand the codebase context and patterns
  2. Identify areas for improvement based on code review feedback
  3. Consider potential impacts of changes based on blast radius analysis
  4. Generate improved code that addresses issues while minimizing negative impacts
  5. Provide explanations for the changes made

Usage: python code_generation_agent.py --repo /path/to/repo --file file.py --review review.json --impact impact.json
"""

import os
import sys
import argparse
import json
import logging
import colorama
from colorama import Fore, Style
from pathlib import Path
from typing import Dict, List, Any, Optional
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

def generate_improved_code(
    arc: Arc, 
    repo_path: str, 
    file_path: str, 
    review_data: Dict[str, Any], 
    impact_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate improved code based on code review and impact analysis.

    Args:
        arc: Initialized Arc instance
        repo_path: Path to the local repository
        file_path: Path to the file to improve
        review_data: Code review results
        impact_data: Impact analysis results

    Returns:
        Dictionary with improved code and explanations
    """
    print(f"{Fore.BLUE}Generating improved code...{Style.RESET_ALL}")

    # Create a progress tracker
    progress = ProgressTracker(5)  # 5 steps: context gathering, code analysis, improvement generation, validation, finalization

    # Get the original file content
    original_content = get_file_content(file_path)
    if not original_content:
        return {
            "success": False,
            "error": f"Could not read file {file_path}",
            "improved_code": "",
            "explanations": []
        }

    # Step 1: Gather context from the knowledge graph
    progress.update("Gathering context from knowledge graph")
    
    # Get decision trail for the file
    try:
        decision_trail = arc.get_decision_trail(file_path=file_path, line_number=1)
        decision_context = ""
        if decision_trail:
            decision_context = "File history:\n"
            for entry in decision_trail[:3]:  # Limit to first 3 entries
                if hasattr(entry, 'rationale') and entry.rationale:
                    decision_context += f"- {entry.rationale}\n"
    except Exception as e:
        decision_context = f"Could not get decision trail: {e}\n"
    
    # Get related components
    try:
        component_id = f"file:{file_path}"
        related_entities = arc.get_related_entities(component_id)
        related_context = ""
        if related_entities:
            related_context = "Related components:\n"
            for entity in related_entities[:5]:  # Limit to first 5 entities
                if hasattr(entity, 'title') and entity.title:
                    relationship = entity.relationship if hasattr(entity, 'relationship') else 'related'
                    related_context += f"- {entity.title} ({relationship})\n"
    except Exception as e:
        related_context = f"Could not get related components: {e}\n"

    # Step 2: Extract insights from code review and impact analysis
    progress.update("Extracting insights from review and impact analysis")
    
    # Extract code review insights
    review_insights = ""
    file_name = os.path.basename(file_path)
    if "file_reviews" in review_data and file_name in review_data["file_reviews"]:
        file_review = review_data["file_reviews"][file_name]
        if "answer" in file_review and file_review["answer"]:
            review_insights = f"Code review insights:\n{file_review['answer']}\n"
    
    # Extract impact analysis insights
    impact_insights = ""
    if "assessment" in impact_data and impact_data["assessment"]:
        impact_insights = f"Impact analysis insights:\n{impact_data['assessment']}\n"
    
    # Step 3: Generate improved code
    progress.update("Generating improved code")
    
    # Prepare the query for the LLM
    query = f"""
    I'm improving the file {file_path} based on code review and impact analysis.
    
    Here's the original code:
    ```
    {original_content}
    ```
    
    Here's what I know about this file from the knowledge graph:
    {decision_context}
    {related_context}
    
    Code review insights:
    {review_insights}
    
    Impact analysis insights:
    {impact_insights}
    
    Please generate an improved version of this code that:
    1. Addresses the issues identified in the code review
    2. Minimizes negative impacts identified in the impact analysis
    3. Follows best practices and patterns used in the codebase
    4. Maintains compatibility with dependent components
    
    For each significant change, provide a brief explanation of:
    - What was changed
    - Why it was changed
    - How it improves the code
    
    Return the improved code and explanations in a structured format.
    """
    
    try:
        # Use the query method which leverages LLMs to process natural language against the graph
        generation_results = arc.query(query)
        
        # Step 4: Extract and validate the improved code
        progress.update("Validating improved code")
        
        # Extract the improved code and explanations
        improved_code = ""
        explanations = []
        
        if hasattr(generation_results, "answer"):
            answer = generation_results.answer
            
            # Parse the answer as JSON
            try:
                response_data = json.loads(answer)
                improved_code = response_data.get("code", "").strip()
                explanations = response_data.get("explanations", [])
            except json.JSONDecodeError:
                raise ValueError("Failed to parse LLM response as JSON. Ensure the response is properly formatted.")
        
        # Step 5: Finalize the results
        progress.update("Finalizing results")
        
        # Create the result dictionary
        result = {
            "success": True,
            "original_code": original_content,
            "improved_code": improved_code,
            "explanations": explanations,
            "reasoning": generation_results.reasoning if hasattr(generation_results, "reasoning") else ""
        }
        
        progress.complete()
        return result
        
    except Exception as e:
        print(f"\n{Fore.YELLOW}Error generating improved code: {e}{Style.RESET_ALL}")
        progress.complete()
        return {
            "success": False,
            "error": str(e),
            "improved_code": "",
            "explanations": []
        }

def display_results(results: Dict[str, Any]) -> None:
    """Display the code generation results in a readable format.

    Args:
        results: Code generation results dictionary
    """
    print(f"\n{Fore.GREEN}=== Code Generation Results ==={Style.RESET_ALL}\n")
    
    if not results["success"]:
        print(f"{Fore.RED}Error: {results['error']}{Style.RESET_ALL}")
        return
    
    # Display explanations
    print(f"{Fore.CYAN}Improvement Explanations:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 25}{Style.RESET_ALL}")
    for i, explanation in enumerate(results["explanations"], 1):
        if explanation:
            print(f"{i}. {explanation}")
    print()
    
    # Display improved code
    print(f"{Fore.CYAN}Improved Code:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 13}{Style.RESET_ALL}")
    print(f"{results['improved_code']}")
    print()

def main():
    """Main entry point for the Code Generation Agent."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Code Generation Agent using Arc Memory")
    parser.add_argument("--repo", required=True, help="Path to the local repository")
    parser.add_argument("--file", required=True, help="File to improve")
    parser.add_argument("--review", required=True, help="JSON file with code review results")
    parser.add_argument("--impact", required=True, help="JSON file with impact analysis results")
    parser.add_argument("--output", help="Output file for improved code (optional)")
    parser.add_argument("--api-key", help="OpenAI API key (uses OPENAI_API_KEY env var if not provided)")
    
    args = parser.parse_args()
    
    # Initialize Arc Memory
    arc = initialize_arc(args.repo, args.api_key)
    
    # Load code review results
    try:
        with open(args.review, 'r') as f:
            review_data = json.load(f)
    except Exception as e:
        print(f"{Fore.RED}Error loading code review results: {e}{Style.RESET_ALL}")
        sys.exit(1)
    
    # Load impact analysis results
    try:
        with open(args.impact, 'r') as f:
            impact_data = json.load(f)
    except Exception as e:
        print(f"{Fore.RED}Error loading impact analysis results: {e}{Style.RESET_ALL}")
        sys.exit(1)
    
    # Generate improved code
    results = generate_improved_code(arc, args.repo, args.file, review_data, impact_data)
    
    # Display results
    display_results(results)
    
    # Save improved code to a file if requested
    if args.output and results["success"]:
        try:
            with open(args.output, 'w') as f:
                f.write(results["improved_code"])
            print(f"{Fore.GREEN}Improved code saved to {args.output}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error saving improved code: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
