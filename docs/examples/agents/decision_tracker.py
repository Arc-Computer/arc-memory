#!/usr/bin/env python3
"""
Decision Tracker Agent

This example creates an agent that explains why code exists and tracks decision trails
throughout the codebase.

Usage:
    python decision_tracker.py

Requirements:
    - Arc Memory installed and configured
    - OpenAI API key set as OPENAI_API_KEY environment variable
"""

import os
import argparse
from arc_memory import Arc
from arc_memory.sdk.adapters import get_adapter

def create_decision_tracker_agent(repo_path="./", model="gpt-4o"):
    """
    Create a decision tracker agent that explains why code exists and tracks decision trails.
    
    Args:
        repo_path: Path to the repository
        model: OpenAI model to use
        
    Returns:
        A function that takes a query and returns a response
    """
    # Initialize Arc with the repository path
    arc = Arc(repo_path=repo_path)
    
    # Get the OpenAI adapter
    openai_adapter = get_adapter("openai")
    
    # Choose which Arc Memory functions to expose
    arc_functions = [
        arc.query,                    # Natural language queries
        arc.get_decision_trail,       # Trace code history
        arc.get_entity_details,       # Get entity details
        arc.get_related_entities      # Find connections
    ]
    
    # Convert to OpenAI tools
    tools = openai_adapter.adapt_functions(arc_functions)
    
    # Create an OpenAI agent
    agent = openai_adapter.create_agent(
        tools=tools,
        model=model,
        system_message="""
        You are a decision tracking assistant with access to Arc Memory.
        
        Help the developer understand why code exists and the decisions that led to its current state.
        
        Focus on:
        1. Tracing the history of code and its evolution
        2. Explaining the rationale behind key decisions
        3. Connecting code to issues, PRs, and discussions
        4. Identifying the stakeholders involved in decisions
        
        Be thorough and evidence-based. Provide specific examples from the codebase.
        """
    )
    
    return agent

def main():
    parser = argparse.ArgumentParser(description="Decision Tracker Agent")
    parser.add_argument("--repo", default="./", help="Path to the repository")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--file", help="File to analyze")
    parser.add_argument("--line", type=int, help="Line number to analyze")
    args = parser.parse_args()
    
    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY=your-api-key")
        return
    
    # Create the decision tracker agent
    agent = create_decision_tracker_agent(repo_path=args.repo, model=args.model)
    
    if args.file and args.line:
        # Analyze a specific file and line
        query = f"What's the decision trail for {args.file} line {args.line}? Why does this code exist and what decisions led to its current state?"
        print(f"\nAnalyzing {args.file} line {args.line}...\n")
        response = agent(query)
        print(response)
    elif args.file:
        # Analyze a specific file
        query = f"What's the history of {args.file}? Why was it created and how has it evolved over time?"
        print(f"\nAnalyzing {args.file}...\n")
        response = agent(query)
        print(response)
    else:
        # Interactive mode
        print("\nDecision Tracker Agent")
        print("=====================")
        print("Ask questions about why code exists and the decisions behind it.")
        print("Type 'exit' to quit.\n")
        
        while True:
            query = input("\nQuestion: ")
            if query.lower() in ["exit", "quit", "q"]:
                break
            
            response = agent(query)
            print("\nResponse:")
            print(response)

if __name__ == "__main__":
    main()
