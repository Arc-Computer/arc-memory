#!/usr/bin/env python3
"""
OpenAI Integration Example

This example demonstrates how to integrate Arc Memory with OpenAI's API.

Usage:
    python openai_integration.py

Requirements:
    - Arc Memory installed and configured
    - OpenAI API key set as OPENAI_API_KEY environment variable
"""

import os
import argparse
from arc_memory import Arc
from arc_memory.sdk.adapters import get_adapter

def create_openai_agent(repo_path="./", model="gpt-4o"):
    """
    Create an OpenAI agent with Arc Memory tools.
    
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
        arc.get_related_entities,     # Find connections
        arc.get_entity_details,       # Get entity details
        arc.analyze_component_impact  # Analyze impact
    ]
    
    # Convert to OpenAI tools
    tools = openai_adapter.adapt_functions(arc_functions)
    
    # Create an OpenAI agent
    agent = openai_adapter.create_agent(
        tools=tools,
        model=model,
        system_message="You are a helpful assistant with access to Arc Memory."
    )
    
    return agent

def create_openai_assistant(repo_path="./", model="gpt-4o"):
    """
    Create an OpenAI Assistant with Arc Memory tools.
    
    Args:
        repo_path: Path to the repository
        model: OpenAI model to use
        
    Returns:
        An OpenAI Assistant that can answer questions about the codebase
    """
    # Initialize Arc with the repository path
    arc = Arc(repo_path=repo_path)
    
    # Get the OpenAI adapter
    openai_adapter = get_adapter("openai")
    
    # Choose which Arc Memory functions to expose
    arc_functions = [
        arc.query,                    # Natural language queries
        arc.get_decision_trail,       # Trace code history
        arc.get_related_entities,     # Find connections
        arc.get_entity_details,       # Get entity details
        arc.analyze_component_impact  # Analyze impact
    ]
    
    # Convert to OpenAI tools
    tools = openai_adapter.adapt_functions(arc_functions)
    
    # Create an OpenAI Assistant
    assistant = openai_adapter.create_assistant(
        tools=tools,
        name="Arc Memory Assistant",
        instructions="You are a helpful assistant with access to Arc Memory.",
        model=model
    )
    
    return assistant

def main():
    parser = argparse.ArgumentParser(description="OpenAI Integration Example")
    parser.add_argument("--repo", default="./", help="Path to the repository")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--assistant", action="store_true", help="Use OpenAI Assistant API instead of function calling")
    args = parser.parse_args()
    
    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY=your-api-key")
        return
    
    if args.assistant:
        # Create an OpenAI Assistant
        print("\nCreating OpenAI Assistant...\n")
        assistant = create_openai_assistant(repo_path=args.repo, model=args.model)
        print(f"Assistant created with ID: {assistant.id}")
        print("\nTo use this assistant:")
        print("1. Go to https://platform.openai.com/assistants")
        print(f"2. Find the assistant named 'Arc Memory Assistant'")
        print("3. Start a conversation with it")
        print("\nNote: The assistant will have access to your Arc Memory knowledge graph.")
    else:
        # Create an OpenAI agent
        print("\nCreating OpenAI agent...\n")
        agent = create_openai_agent(repo_path=args.repo, model=args.model)
        
        # Interactive mode
        print("\nOpenAI Integration Example")
        print("=========================")
        print("Ask questions about your codebase.")
        print("Type 'exit' to quit.\n")
        
        while True:
            query = input("\nQuestion: ")
            if query.lower() in ["exit", "quit", "q"]:
                break
            
            # Function calling approach
            response = agent(query)
            print("\nResponse:")
            print(response)

if __name__ == "__main__":
    main()
