#!/usr/bin/env python3
"""
LangChain Integration Example

This example demonstrates how to integrate Arc Memory with LangChain.

Usage:
    python langchain_integration.py

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
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    print("Error: langchain packages not installed")
    print("Please install them with: pip install langchain-core langchain-openai")
    exit(1)

def create_langchain_agent(repo_path="./", model="gpt-4o", verbose=False):
    """
    Create a LangChain agent with Arc Memory tools.

    Args:
        repo_path: Path to the repository
        model: OpenAI model to use
        verbose: Whether to enable verbose output

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
        arc.get_decision_trail,       # Trace code history
        arc.get_related_entities,     # Find connections
        arc.get_entity_details,       # Get entity details
        arc.analyze_component_impact  # Analyze impact
    ]

    # Convert to LangChain tools
    tools = langchain_adapter.adapt_functions(arc_functions)

    # Create a LangChain agent
    llm = ChatOpenAI(model=model)
    agent = langchain_adapter.create_agent(
        tools=tools,
        llm=llm,
        system_message="You are a helpful assistant with access to Arc Memory.",
        verbose=verbose
    )

    return agent

def create_langgraph_agent(repo_path="./", model="gpt-4o", verbose=False):
    """
    Create a LangGraph agent with Arc Memory tools.

    Args:
        repo_path: Path to the repository
        model: OpenAI model to use
        verbose: Whether to enable verbose output

    Returns:
        A LangGraph agent that can answer questions about the codebase
    """
    # Initialize Arc with the repository path
    arc = Arc(repo_path=repo_path)

    # Get the LangChain adapter
    langchain_adapter = get_adapter("langchain")

    # Choose which Arc Memory functions to expose
    arc_functions = [
        arc.query,                    # Natural language queries
        arc.get_decision_trail,       # Trace code history
        arc.get_related_entities,     # Find connections
        arc.get_entity_details,       # Get entity details
        arc.analyze_component_impact  # Analyze impact
    ]

    # Convert to LangChain tools
    tools = langchain_adapter.adapt_functions(arc_functions)

    # Create a LangGraph agent
    llm = ChatOpenAI(model=model)
    agent = langchain_adapter.create_agent(
        tools=tools,
        llm=llm,
        system_message="You are a helpful assistant with access to Arc Memory.",
        verbose=verbose,
        use_langgraph=True  # Explicitly use LangGraph
    )

    return agent

def main():
    parser = argparse.ArgumentParser(description="LangChain Integration Example")
    parser.add_argument("--repo", default="./", help="Path to the repository")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--langgraph", action="store_true", help="Use LangGraph instead of AgentExecutor")
    args = parser.parse_args()

    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY=your-api-key")
        return

    # Create the appropriate agent
    if args.langgraph:
        print("\nCreating LangGraph agent...\n")
        agent = create_langgraph_agent(repo_path=args.repo, model=args.model, verbose=args.verbose)
    else:
        print("\nCreating LangChain agent...\n")
        agent = create_langchain_agent(repo_path=args.repo, model=args.model, verbose=args.verbose)

    # Interactive mode
    print("\nLangChain Integration Example")
    print("============================")
    print("Ask questions about your codebase.")
    print("Type 'exit' to quit.\n")

    while True:
        query = input("\nQuestion: ")
        if query.lower() in ["exit", "quit", "q"]:
            break

        if args.langgraph:
            # LangGraph approach
            response = agent.invoke([
                SystemMessage(content="You are a helpful assistant with access to Arc Memory."),
                HumanMessage(content=query)
            ])
            print("\nResponse:")
            print(response.content)
        else:
            # AgentExecutor approach
            response = agent.invoke({"input": query})
            print("\nResponse:")
            print(response["output"])

if __name__ == "__main__":
    main()
