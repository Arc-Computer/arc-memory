#!/usr/bin/env python3
"""
Onboarding Agent

This example creates an agent that helps new team members understand the codebase
by explaining components, architecture, and key decisions.

Usage:
    python onboarding_agent.py

Requirements:
    - Arc Memory installed and configured
    - LangChain and OpenAI packages installed
    - OpenAI API key set as OPENAI_API_KEY environment variable
"""

import os
import argparse
from arc_memory import Arc
from arc_memory.sdk.adapters import get_adapter

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    print("Error: langchain_openai package not installed")
    print("Please install it with: pip install langchain langchain-openai")
    exit(1)

def create_onboarding_agent(repo_path="./", model="gpt-4o"):
    """
    Create an onboarding agent that helps new team members understand the codebase.
    
    Args:
        repo_path: Path to the repository
        model: OpenAI model to use
        
    Returns:
        A LangChain agent that can answer questions about the codebase
    """
    # Initialize Arc with the repository path
    arc = Arc(repo_path=repo_path)
    
    # Get the LangChain adapter
    langchain_adapter = get_adapter("langchain")
    
    # Choose which Arc Memory functions to expose
    arc_functions = [
        arc.query,                    # Natural language queries
        arc.get_entity_details,       # Get entity details
        arc.get_related_entities,     # Find connections
        arc.get_decision_trail        # Trace code history
    ]
    
    # Convert to LangChain tools
    tools = langchain_adapter.adapt_functions(arc_functions)
    
    # Create a LangChain agent
    llm = ChatOpenAI(model=model)
    agent = langchain_adapter.create_agent(
        tools=tools,
        llm=llm,
        system_message="""
        You are an onboarding assistant with access to Arc Memory.
        
        Help new team members understand the codebase and its architecture.
        
        Focus on:
        1. Explaining the purpose and structure of components
        2. Identifying key relationships between components
        3. Providing context about important decisions and their rationale
        4. Guiding the developer through the most important parts of the codebase
        
        Be educational and supportive. Provide specific examples and evidence from the codebase.
        """
    )
    
    return agent

def main():
    parser = argparse.ArgumentParser(description="Onboarding Agent")
    parser.add_argument("--repo", default="./", help="Path to the repository")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--component", help="Component to learn about")
    args = parser.parse_args()
    
    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY=your-api-key")
        return
    
    # Create the onboarding agent
    agent = create_onboarding_agent(repo_path=args.repo, model=args.model)
    
    if args.component:
        # Learn about a specific component
        query = f"I'm new to the team. Can you explain the {args.component} component? What's its purpose, structure, and how does it relate to other parts of the codebase?"
        print(f"\nLearning about {args.component}...\n")
        response = agent.invoke({"input": query})
        print(response["output"])
    else:
        # Interactive mode
        print("\nOnboarding Agent")
        print("================")
        print("Ask questions to learn about the codebase.")
        print("Type 'exit' to quit.\n")
        
        while True:
            query = input("\nQuestion: ")
            if query.lower() in ["exit", "quit", "q"]:
                break
            
            response = agent.invoke({"input": query})
            print("\nResponse:")
            print(response["output"])

if __name__ == "__main__":
    main()
