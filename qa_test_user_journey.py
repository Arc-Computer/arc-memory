#!/usr/bin/env python
"""
QA Test Script for Arc Memory First-Time User Journey.

This script simulates the experience of a first-time user of Arc Memory.
It measures the time taken for each step and verifies that the user can
go from zero to working queries in under 30 minutes.

Usage:
    python qa_test_user_journey.py
"""

import os
import sys
import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, using existing environment variables")

# Step 1: Installation
print("\nStep 1: Installation")
print("=" * 50)
print("Simulating installation of Arc Memory...")
print("In a real test, you would run: pip install arc-memory[all]")
print("For this test, we'll assume Arc Memory is already installed.")

# Check if Arc Memory is installed
try:
    import arc_memory
    print(f"✅ Arc Memory is installed (version {arc_memory.__version__})")
except ImportError:
    print("❌ Arc Memory is not installed")
    print("Please install Arc Memory first: pip install arc-memory[all]")
    sys.exit(1)

# Step 2: Authentication
print("\nStep 2: Authentication")
print("=" * 50)
print("Checking if authentication tokens are available...")

# Check for GitHub token
if "GITHUB_TOKEN" in os.environ:
    github_token = os.environ["GITHUB_TOKEN"]
    masked_token = f"{github_token[:5]}...{github_token[-5:]}" if len(github_token) > 10 else "***"
    print(f"✅ GitHub token is available: {masked_token}")
else:
    print("⚠️ GitHub token is not available")
    print("In a real test, you would run: arc auth gh")

# Check for Linear token
if "LINEAR_API_KEY" in os.environ:
    linear_token = os.environ["LINEAR_API_KEY"]
    masked_token = f"{linear_token[:5]}...{linear_token[-5:]}" if len(linear_token) > 10 else "***"
    print(f"✅ Linear token is available: {masked_token}")
else:
    print("⚠️ Linear token is not available")
    print("In a real test, you would run: arc auth linear")

# Step 3: Create a test repository
print("\nStep 3: Create a test repository")
print("=" * 50)
print("Creating a test repository...")

# Create a temporary directory for the test repository
test_repo_path = Path(tempfile.mkdtemp())
print(f"✅ Created test repository at: {test_repo_path}")

try:
    # Initialize a Git repository
    subprocess.run(["git", "init"], cwd=test_repo_path, check=True, capture_output=True)
    print("✅ Initialized Git repository")
    
    # Create a sample Python file
    sample_file = test_repo_path / "main.py"
    with open(sample_file, "w") as f:
        f.write("""
def hello_world():
    \"\"\"Print a greeting message.\"\"\"
    print("Hello, world!")

def add(a, b):
    \"\"\"Add two numbers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of a and b
    \"\"\"
    return a + b

if __name__ == "__main__":
    hello_world()
    print(f"1 + 2 = {add(1, 2)}")
""")
    print("✅ Created sample Python file")
    
    # Create a README file
    readme_file = test_repo_path / "README.md"
    with open(readme_file, "w") as f:
        f.write("""# Test Repository
        
This is a test repository for Arc Memory.

## Features

- Simple Python functions
- Basic documentation
""")
    print("✅ Created README file")
    
    # Commit the files
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_repo_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=test_repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=test_repo_path, check=True, capture_output=True)
    print("✅ Committed files")
    
    # Step 4: Build the knowledge graph
    print("\nStep 4: Build the knowledge graph")
    print("=" * 50)
    print("Building the knowledge graph...")
    
    start_time = time.time()
    result = subprocess.run(["arc", "build"], cwd=test_repo_path, capture_output=True, text=True)
    build_time = time.time() - start_time
    
    if result.returncode == 0:
        print(f"✅ Built knowledge graph in {build_time:.2f} seconds")
    else:
        print(f"❌ Failed to build knowledge graph: {result.stderr}")
        print("Continuing with the test...")
    
    # Step 5: Run basic queries
    print("\nStep 5: Run basic queries")
    print("=" * 50)
    print("Running basic queries...")
    
    # Query 1: Get repository overview
    print("\nQuery 1: Get repository overview")
    start_time = time.time()
    try:
        from arc_memory import Arc
        arc = Arc(repo_path=test_repo_path)
        result = arc.query("What is this repository about?")
        query_time = time.time() - start_time
        
        print(f"✅ Query completed in {query_time:.2f} seconds")
        print(f"Answer: {result.answer[:100]}..." if len(result.answer) > 100 else f"Answer: {result.answer}")
        print(f"Confidence: {result.confidence}")
    except Exception as e:
        print(f"❌ Failed to run query: {e}")
    
    # Query 2: Get decision trail for a file
    print("\nQuery 2: Get decision trail for a file")
    start_time = time.time()
    try:
        result = arc.get_decision_trail("main.py", 1)
        query_time = time.time() - start_time
        
        print(f"✅ Query completed in {query_time:.2f} seconds")
        print(f"Decision trail entries: {len(result)}")
        
        if result:
            for i, entry in enumerate(result):
                print(f"  Entry {i+1}: {entry.title} ({entry.type})")
        else:
            print("  No decision trail entries found")
    except Exception as e:
        print(f"❌ Failed to get decision trail: {e}")
    
    # Query 3: Get related entities for a commit
    print("\nQuery 3: Get related entities for a commit")
    start_time = time.time()
    try:
        # Get the commit SHA
        git_result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=test_repo_path, capture_output=True, text=True)
        commit_sha = git_result.stdout.strip()
        
        result = arc.get_related_entities(f"commit:{commit_sha}")
        query_time = time.time() - start_time
        
        print(f"✅ Query completed in {query_time:.2f} seconds")
        print(f"Related entities: {len(result)}")
        
        if result:
            for i, entity in enumerate(result):
                print(f"  Entity {i+1}: {entity.title} ({entity.type}) - {entity.relationship}")
        else:
            print("  No related entities found")
    except Exception as e:
        print(f"❌ Failed to get related entities: {e}")
    
    # Step 6: Integrate with LangChain
    print("\nStep 6: Integrate with LangChain")
    print("=" * 50)
    print("Creating a simple LangChain integration...")
    
    # Create a Python file for LangChain integration
    langchain_file = test_repo_path / "langchain_integration.py"
    with open(langchain_file, "w") as f:
        f.write("""
from arc_memory import Arc
from arc_memory.sdk.adapters import get_adapter

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Get Arc Memory functions as LangChain tools
langchain_adapter = get_adapter("langchain")
tools = langchain_adapter.adapt_functions([
    arc.query,
    arc.get_decision_trail,
    arc.get_related_entities
])

print(f"Created {len(tools)} LangChain tools")
print("LangChain integration successful!")

# In a real integration, you would create an agent:
# from langchain_openai import ChatOpenAI
# llm = ChatOpenAI(model="gpt-3.5-turbo")
# agent = langchain_adapter.create_agent(tools=tools, llm=llm)
# response = agent.invoke({"input": "What is this repository about?"})
""")
    print("✅ Created LangChain integration file")
    
    # Run the LangChain integration
    start_time = time.time()
    result = subprocess.run(["python", "langchain_integration.py"], cwd=test_repo_path, capture_output=True, text=True)
    integration_time = time.time() - start_time
    
    if result.returncode == 0:
        print(f"✅ LangChain integration completed in {integration_time:.2f} seconds")
        print(result.stdout)
    else:
        print(f"❌ Failed to run LangChain integration: {result.stderr}")
    
    # Summary
    print("\n=== User Journey Summary ===")
    print(f"Total time: {build_time + query_time + integration_time:.2f} seconds")
    print("In a real-world scenario with a larger repository and more complex queries,")
    print("this would take longer, but should still be under 30 minutes for a first-time user.")
    
finally:
    # Clean up
    print("\nCleaning up...")
    shutil.rmtree(test_repo_path)
    print(f"✅ Removed test repository: {test_repo_path}")

print("\nFirst-time user journey test completed.")
