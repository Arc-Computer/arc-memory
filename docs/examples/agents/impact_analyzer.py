#!/usr/bin/env python3
"""
Impact Analyzer Agent

This example creates an agent that analyzes the potential impact of code changes
on other components in the codebase.

Usage:
    python impact_analyzer.py

Requirements:
    - Arc Memory installed and configured
    - OpenAI API key set as OPENAI_API_KEY environment variable
"""

import os
import argparse
from arc_memory import Arc
from arc_memory.sdk.adapters import get_adapter

def create_impact_analyzer_agent(repo_path="./", model="gpt-4o"):
    """
    Create an impact analyzer agent that analyzes the potential impact of code changes.
    
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
        arc.analyze_component_impact,  # Analyze impact
        arc.get_related_entities,      # Find connections
        arc.get_entity_details,        # Get entity details
        arc.query                      # Natural language queries
    ]
    
    # Convert to OpenAI tools
    tools = openai_adapter.adapt_functions(arc_functions)
    
    # Create an OpenAI agent
    agent = openai_adapter.create_agent(
        tools=tools,
        model=model,
        system_message="""
        You are an impact analysis assistant with access to Arc Memory.
        
        Help the developer understand the potential impact of code changes on other components.
        
        Focus on:
        1. Identifying direct dependencies that might be affected
        2. Discovering indirect dependencies that could be impacted
        3. Assessing the risk level of proposed changes
        4. Suggesting tests that should be run to verify changes
        
        Be thorough and specific. Provide concrete examples and evidence from the codebase.
        """
    )
    
    return agent

def main():
    parser = argparse.ArgumentParser(description="Impact Analyzer Agent")
    parser.add_argument("--repo", default="./", help="Path to the repository")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--component", help="Component to analyze")
    args = parser.parse_args()
    
    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY=your-api-key")
        return
    
    # Create the impact analyzer agent
    agent = create_impact_analyzer_agent(repo_path=args.repo, model=args.model)
    
    if args.component:
        # Analyze a specific component
        query = f"What would be the impact of changing {args.component}? Which components depend on it directly and indirectly? What's the risk level?"
        print(f"\nAnalyzing impact of changes to {args.component}...\n")
        response = agent(query)
        print(response)
    else:
        # Interactive mode
        print("\nImpact Analyzer Agent")
        print("====================")
        print("Ask questions about the potential impact of code changes.")
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
