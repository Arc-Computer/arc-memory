#!/usr/bin/env python3
"""
Self-Healing Code Generation Loop

An orchestration system that coordinates three specialized agents to create a self-healing
code generation loop. The system leverages Arc Memory's knowledge graph and OpenAI's
agent orchestration capabilities to:
  1. Review code using the Code Review Agent
  2. Analyze potential impacts using the Blast Radius Analysis Agent
  3. Generate improved code using the Code Generation Agent
  4. Validate the improvements and provide feedback

This creates a continuous improvement loop where code is iteratively enhanced
based on insights from the knowledge graph and specialized agents.

Usage: python self_healing_loop.py --repo /path/to/repo --file file.py [--iterations 3]
"""

import os
import sys
import argparse
import json
import logging
import tempfile
import colorama
from colorama import Fore, Style
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import time
import subprocess

from arc_memory.sdk import Arc
from arc_memory.sdk.adapters import get_adapter

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

def create_openai_orchestrator(arc: Arc, system_message: str = None) -> Any:
    """Create an OpenAI agent for orchestration.

    Args:
        arc: Initialized Arc instance
        system_message: Custom system message for the agent

    Returns:
        OpenAI agent function
    """
    # Get the OpenAI adapter
    openai_adapter = get_adapter("openai")
    
    # Choose which Arc Memory functions to expose
    arc_functions = [
        arc.query,
        arc.get_decision_trail,
        arc.get_related_entities,
        arc.get_entity_details,
        arc.analyze_component_impact
    ]
    
    # Adapt the functions for OpenAI
    tools = openai_adapter.adapt_functions(arc_functions)
    
    # Set default system message if none provided
    if not system_message:
        system_message = """
        You are an orchestration agent that coordinates a self-healing code generation loop.
        You have access to Arc Memory's knowledge graph and can use it to gather context about the codebase.
        Your goal is to coordinate three specialized agents to improve code quality:
        1. Code Review Agent - Analyzes code quality, patterns, and potential issues
        2. Blast Radius Analysis Agent - Analyzes potential impacts of changes
        3. Code Generation Agent - Generates improved code based on insights
        
        You should make decisions about when to run each agent and how to interpret their results.
        """
    
    # Create the OpenAI agent
    agent = openai_adapter.create_agent(
        tools=tools,
        model="gpt-4.1",
        temperature=0,
        system_message=system_message
    )
    
    return agent

def run_code_review_agent(repo_path: str, file_path: str) -> Dict[str, Any]:
    """Run the Code Review Agent on a file.

    Args:
        repo_path: Path to the local repository
        file_path: Path to the file to review

    Returns:
        Code review results as a dictionary
    """
    print(f"{Fore.BLUE}Running Code Review Agent on {file_path}...{Style.RESET_ALL}")
    
    # Create a temporary file for the results
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
        output_path = temp_file.name
    
    # Build the command to run the Code Review Agent
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_powered_code_review.py")
    command = [
        sys.executable,
        script_path,
        "--repo", repo_path,
        "--files", file_path,
        "--output", output_path
    ]
    
    # Run the command
    try:
        subprocess.run(command, check=True, capture_output=True)
        
        # Load the results
        with open(output_path, 'r') as f:
            results = json.load(f)
        
        # Clean up the temporary file
        os.unlink(output_path)
        
        return results
    
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error running Code Review Agent: {e}{Style.RESET_ALL}")
        print(f"stdout: {e.stdout.decode('utf-8')}")
        print(f"stderr: {e.stderr.decode('utf-8')}")
        return {"error": str(e)}
    
    except Exception as e:
        print(f"{Fore.RED}Error running Code Review Agent: {e}{Style.RESET_ALL}")
        return {"error": str(e)}

def run_blast_radius_agent(repo_path: str, file_path: str) -> Dict[str, Any]:
    """Run the Blast Radius Analysis Agent on a file.

    Args:
        repo_path: Path to the local repository
        file_path: Path to the file to analyze

    Returns:
        Impact analysis results as a dictionary
    """
    print(f"{Fore.BLUE}Running Blast Radius Analysis Agent on {file_path}...{Style.RESET_ALL}")
    
    # Create a temporary file for the results
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
        output_path = temp_file.name
    
    # Build the command to run the Blast Radius Analysis Agent
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "enhanced_blast_radius.py")
    
    # Since enhanced_blast_radius.py doesn't have a JSON output option,
    # we'll need to capture its output and parse it
    command = [
        sys.executable,
        script_path,
        file_path,
        "--repo", repo_path
    ]
    
    # Run the command
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        
        # Parse the output to extract the LLM analysis
        output = result.stdout
        
        # Extract the LLM analysis section
        import re
        analysis_section = re.search(r'LLM Analysis of Impact:.*?(?=\n\n|$)', output, re.DOTALL)
        
        if analysis_section:
            analysis_text = analysis_section.group(0)
            
            # Create a simplified result dictionary
            results = {
                "assessment": analysis_text,
                "success": True
            }
        else:
            results = {
                "assessment": "No LLM analysis found in the output.",
                "success": False
            }
        
        # Save the results to the temporary file
        with open(output_path, 'w') as f:
            json.dump(results, f)
        
        return results
    
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error running Blast Radius Analysis Agent: {e}{Style.RESET_ALL}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return {"error": str(e), "success": False}
    
    except Exception as e:
        print(f"{Fore.RED}Error running Blast Radius Analysis Agent: {e}{Style.RESET_ALL}")
        return {"error": str(e), "success": False}

def run_code_generation_agent(
    repo_path: str, 
    file_path: str, 
    review_results: Dict[str, Any], 
    impact_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Run the Code Generation Agent on a file.

    Args:
        repo_path: Path to the local repository
        file_path: Path to the file to improve
        review_results: Code review results
        impact_results: Impact analysis results

    Returns:
        Code generation results as a dictionary
    """
    print(f"{Fore.BLUE}Running Code Generation Agent on {file_path}...{Style.RESET_ALL}")
    
    # Create temporary files for the inputs and output
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as review_file:
        review_path = review_file.name
        json.dump(review_results, review_file)
    
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as impact_file:
        impact_path = impact_file.name
        json.dump(impact_results, impact_file)
    
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as output_file:
        output_path = output_file.name
    
    # Build the command to run the Code Generation Agent
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_generation_agent.py")
    command = [
        sys.executable,
        script_path,
        "--repo", repo_path,
        "--file", file_path,
        "--review", review_path,
        "--impact", impact_path,
        "--output", output_path
    ]
    
    # Run the command
    try:
        subprocess.run(command, check=True, capture_output=True)
        
        # Load the results
        with open(output_path, 'r') as f:
            results = json.load(f)
        
        # Clean up the temporary files
        os.unlink(review_path)
        os.unlink(impact_path)
        os.unlink(output_path)
        
        return results
    
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error running Code Generation Agent: {e}{Style.RESET_ALL}")
        print(f"stdout: {e.stdout.decode('utf-8')}")
        print(f"stderr: {e.stderr.decode('utf-8')}")
        return {"error": str(e), "success": False}
    
    except Exception as e:
        print(f"{Fore.RED}Error running Code Generation Agent: {e}{Style.RESET_ALL}")
        return {"error": str(e), "success": False}

def evaluate_improvement(
    arc: Arc, 
    original_code: str, 
    improved_code: str, 
    file_path: str
) -> Tuple[float, str]:
    """Evaluate the quality of the improved code.

    Args:
        arc: Initialized Arc instance
        original_code: Original code
        improved_code: Improved code
        file_path: Path to the file

    Returns:
        Tuple of (score, feedback) where score is between 0 and 1
    """
    print(f"{Fore.BLUE}Evaluating code improvement...{Style.RESET_ALL}")
    
    # Prepare the query for the LLM
    query = f"""
    I'm evaluating the quality of an improved version of {file_path}.
    
    Original code:
    ```
    {original_code[:1000]}  # Limit to first 1000 chars
    ```
    
    Improved code:
    ```
    {improved_code[:1000]}  # Limit to first 1000 chars
    ```
    
    Please evaluate the improved code on the following criteria:
    1. Correctness - Does it maintain the original functionality?
    2. Quality - Is it better structured, more readable, or more maintainable?
    3. Safety - Does it minimize potential negative impacts on dependent components?
    4. Best practices - Does it follow coding best practices and patterns?
    
    For each criterion, provide a score from 0 to 10 and a brief explanation.
    Then provide an overall score from 0 to 10 and a summary of the evaluation.
    """
    
    try:
        # Use the query method which leverages LLMs to process natural language against the graph
        evaluation_results = arc.query(query)
        
        # Extract the evaluation
        if hasattr(evaluation_results, "answer"):
            answer = evaluation_results.answer
            
            # Extract the overall score
            import re
            score_match = re.search(r'overall score.*?(\d+(?:\.\d+)?)', answer, re.IGNORECASE)
            score = float(score_match.group(1)) / 10.0 if score_match else 0.5
            
            return score, answer
        
        return 0.5, "Could not evaluate the improvement."
    
    except Exception as e:
        print(f"{Fore.YELLOW}Error evaluating improvement: {e}{Style.RESET_ALL}")
        return 0.5, f"Error evaluating improvement: {e}"

def run_self_healing_loop(
    arc: Arc, 
    repo_path: str, 
    file_path: str, 
    iterations: int = 3, 
    improvement_threshold: float = 0.7
) -> Dict[str, Any]:
    """Run the self-healing code generation loop.

    Args:
        arc: Initialized Arc instance
        repo_path: Path to the local repository
        file_path: Path to the file to improve
        iterations: Maximum number of iterations
        improvement_threshold: Minimum improvement score to accept

    Returns:
        Dictionary with the final results
    """
    print(f"{Fore.GREEN}=== Starting Self-Healing Code Generation Loop ==={Style.RESET_ALL}")
    print(f"{Fore.GREEN}File: {file_path}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Max iterations: {iterations}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Improvement threshold: {improvement_threshold}{Style.RESET_ALL}")
    print()
    
    # Get the original file content
    original_content = ""
    with open(file_path, 'r') as f:
        original_content = f.read()
    
    # Initialize the current code to the original
    current_code = original_content
    
    # Initialize the results dictionary
    results = {
        "file_path": file_path,
        "original_code": original_content,
        "iterations": [],
        "final_code": "",
        "improvement_score": 0.0,
        "feedback": ""
    }
    
    # Run the loop for the specified number of iterations
    for i in range(iterations):
        print(f"\n{Fore.CYAN}=== Iteration {i+1}/{iterations} ==={Style.RESET_ALL}\n")
        
        # Step 1: Run the Code Review Agent
        review_results = run_code_review_agent(repo_path, file_path)
        if "error" in review_results:
            print(f"{Fore.RED}Code Review Agent failed: {review_results['error']}{Style.RESET_ALL}")
            break
        
        # Step 2: Run the Blast Radius Analysis Agent
        impact_results = run_blast_radius_agent(repo_path, file_path)
        if "error" in impact_results:
            print(f"{Fore.RED}Blast Radius Analysis Agent failed: {impact_results['error']}{Style.RESET_ALL}")
            break
        
        # Step 3: Run the Code Generation Agent
        generation_results = run_code_generation_agent(repo_path, file_path, review_results, impact_results)
        if "error" in generation_results or not generation_results.get("success", False):
            print(f"{Fore.RED}Code Generation Agent failed: {generation_results.get('error', 'Unknown error')}{Style.RESET_ALL}")
            break
        
        # Step 4: Evaluate the improvement
        improved_code = generation_results.get("improved_code", "")
        if not improved_code:
            print(f"{Fore.YELLOW}No improved code generated.{Style.RESET_ALL}")
            break
        
        score, feedback = evaluate_improvement(arc, current_code, improved_code, file_path)
        
        # Step 5: Record the iteration results
        iteration_result = {
            "iteration": i+1,
            "review_results": review_results,
            "impact_results": impact_results,
            "generation_results": generation_results,
            "improvement_score": score,
            "feedback": feedback
        }
        results["iterations"].append(iteration_result)
        
        print(f"{Fore.YELLOW}Improvement score: {score:.2f}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Feedback: {feedback[:200]}...{Style.RESET_ALL}" if len(feedback) > 200 else f"{Fore.YELLOW}Feedback: {feedback}{Style.RESET_ALL}")
        
        # Step 6: Check if the improvement is good enough
        if score >= improvement_threshold:
            print(f"{Fore.GREEN}Improvement meets threshold ({score:.2f} >= {improvement_threshold}). Accepting changes.{Style.RESET_ALL}")
            current_code = improved_code
            results["final_code"] = improved_code
            results["improvement_score"] = score
            results["feedback"] = feedback
            
            # If this is the last iteration, we're done
            if i == iterations - 1:
                print(f"{Fore.GREEN}Reached maximum iterations. Final improvement score: {score:.2f}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Improvement below threshold ({score:.2f} < {improvement_threshold}). Trying again.{Style.RESET_ALL}")
            
            # If this is the last iteration, use the best improvement so far
            if i == iterations - 1:
                print(f"{Fore.YELLOW}Reached maximum iterations without meeting threshold. Using best improvement.{Style.RESET_ALL}")
                
                # Find the best iteration
                best_iteration = max(results["iterations"], key=lambda x: x["improvement_score"])
                best_score = best_iteration["improvement_score"]
                
                if best_score > 0:
                    print(f"{Fore.GREEN}Best improvement score: {best_score:.2f} (iteration {best_iteration['iteration']}){Style.RESET_ALL}")
                    results["final_code"] = best_iteration["generation_results"]["improved_code"]
                    results["improvement_score"] = best_score
                    results["feedback"] = best_iteration["feedback"]
                else:
                    print(f"{Fore.RED}No acceptable improvements found. Keeping original code.{Style.RESET_ALL}")
                    results["final_code"] = original_content
                    results["improvement_score"] = 0.0
                    results["feedback"] = "No acceptable improvements found."
    
    print(f"\n{Fore.GREEN}=== Self-Healing Loop Complete ==={Style.RESET_ALL}")
    return results

def main():
    """Main entry point for the Self-Healing Code Generation Loop."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Self-Healing Code Generation Loop using Arc Memory")
    parser.add_argument("--repo", required=True, help="Path to the local repository")
    parser.add_argument("--file", required=True, help="File to improve")
    parser.add_argument("--iterations", type=int, default=3, help="Maximum number of iterations (default: 3)")
    parser.add_argument("--threshold", type=float, default=0.7, help="Improvement threshold (default: 0.7)")
    parser.add_argument("--output", help="Output file for improved code (optional)")
    parser.add_argument("--api-key", help="OpenAI API key (uses OPENAI_API_KEY env var if not provided)")
    
    args = parser.parse_args()
    
    # Initialize Arc Memory
    arc = initialize_arc(args.repo, args.api_key)
    
    # Run the self-healing loop
    results = run_self_healing_loop(
        arc, 
        args.repo, 
        args.file, 
        args.iterations, 
        args.threshold
    )
    
    # Save the improved code to a file if requested
    if args.output and results["final_code"]:
        try:
            with open(args.output, 'w') as f:
                f.write(results["final_code"])
            print(f"{Fore.GREEN}Improved code saved to {args.output}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error saving improved code: {e}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}Final improvement score: {results['improvement_score']:.2f}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Self-healing loop completed successfully.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
