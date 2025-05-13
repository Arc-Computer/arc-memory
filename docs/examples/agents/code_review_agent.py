#!/usr/bin/env python3
"""
Code Review Agent

An agent that helps with code reviews by providing historical context and impact analysis.
It answers questions about code history, purpose, and potential effects of changes.

Usage:
    python code_review_agent.py                  # Interactive mode
    python code_review_agent.py --file path/to/file.py  # Review specific file

Requirements:
    - Arc Memory installed: pip install arc-memory[openai]
    - Knowledge graph built: arc build
    - OpenAI API key: export OPENAI_API_KEY=your-key
"""

import os
import argparse
from arc_memory import Arc
from arc_memory.sdk.adapters import get_adapter

def create_code_review_agent(repo_path="./", model="gpt-4o"):
    """
    Create a code review agent that uses Arc Memory to provide context
    and impact analysis for code changes.

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
        system_message="""
        You are a code review assistant with access to Arc Memory.

        Help the developer understand the context and potential impact of code changes.

        When reviewing code, focus on:
        1. The history and rationale behind the code being modified
        2. The potential impact of the changes on other components
        3. Related decisions and discussions that might be relevant

        Be concise but thorough. Provide specific examples and evidence from the codebase.
        """
    )

    return agent

def main():
    parser = argparse.ArgumentParser(description="Code Review Agent")
    parser.add_argument("--repo", default="./", help="Path to the repository")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--file", help="File to review")
    args = parser.parse_args()

    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY=your-api-key")
        return

    # Create the code review agent
    agent = create_code_review_agent(repo_path=args.repo, model=args.model)

    if args.file:
        # Review a specific file
        query = f"I'm reviewing changes to {args.file}. What should I know about this file's history, purpose, and potential impact of changes?"
        print(f"\nReviewing {args.file}...\n")
        response = agent(query)
        print(response)
    else:
        # Interactive mode
        print("\nCode Review Agent")
        print("=================")
        print("Ask questions about code you're reviewing.")
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
